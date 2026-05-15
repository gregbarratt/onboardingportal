from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

try:
    import httpx
except ImportError:  # pragma: no cover - keeps the main portal alive if optional HTTP tooling is missing.
    httpx = None

from app.core.config import settings


METRIC_ENDPOINTS = {
    "cpu": "cpu",
    "cpu_limit": "cpu-limit",
    "memory": "memory",
    "memory_limit": "memory-limit",
    "disk_usage": "disk-usage",
    "disk_capacity": "disk-capacity",
    "http_requests": "http-requests",
    "bandwidth": "bandwidth",
}


class RenderUsageError(RuntimeError):
    """Raised when the Render API cannot return usage data."""


def render_api_is_configured() -> bool:
    return bool(settings.render_api_key.strip())


def get_render_usage_overview() -> dict[str, Any]:
    if not render_api_is_configured():
        return {
            "configured": False,
            "message": "Render usage is not connected yet. Add RENDER_API_KEY in Render to show live usage on this dashboard.",
            "services": [],
            "metric_errors": {},
        }

    try:
        with render_client() as client:
            list_errors: dict[str, str] = {}
            services = safe_list_render_resources(client, "/services", "service", list_errors)
            postgres = safe_list_render_resources(client, "/postgres", "postgres", list_errors)
            disks = safe_list_render_resources(client, "/disks", "disk", list_errors)
            resources = select_monitored_resources(services, postgres, disks)
            attach_metrics(client, resources)
    except RenderUsageError as exc:
        return {
            "configured": True,
            "status": "error",
            "message": str(exc),
            "services": [],
            "metric_errors": {},
        }

    return {
        "configured": True,
        "status": "ok",
        "window_minutes": safe_window_minutes(),
        "service_filter": settings.render_service_name_filter.strip(),
        "services": resources,
        "metric_errors": {**list_errors, **collect_metric_errors(resources)},
        "summary": build_render_summary(resources),
    }


def render_client() -> httpx.Client:
    if httpx is None:
        raise RenderUsageError("The HTTP package for Render usage is not installed yet. Redeploy the backend so requirements are installed.")

    return httpx.Client(
        base_url=settings.render_api_base_url.rstrip("/"),
        headers={
            "Authorization": f"Bearer {settings.render_api_key.strip()}",
            "Accept": "application/json",
        },
        timeout=httpx.Timeout(8.0, connect=4.0),
    )


def safe_list_render_resources(
    client: httpx.Client,
    path: str,
    item_key: str,
    list_errors: dict[str, str],
) -> list[dict[str, Any]]:
    try:
        return list_render_resources(client, path, item_key)
    except RenderUsageError as exc:
        list_errors[path.strip("/")] = str(exc)
        return []


def list_render_resources(client: httpx.Client, path: str, item_key: str) -> list[dict[str, Any]]:
    resources: list[dict[str, Any]] = []
    cursor = None

    for _ in range(5):
        params: dict[str, Any] = {"limit": 100}
        if cursor:
            params["cursor"] = cursor

        payload = render_get(client, path, params=params)
        if not isinstance(payload, list):
            return resources

        next_cursor = None
        for row in payload:
            if not isinstance(row, dict):
                continue
            resource = row.get(item_key) if isinstance(row.get(item_key), dict) else row
            resources.append(resource)
            next_cursor = row.get("cursor") or next_cursor

        if not next_cursor or next_cursor == cursor:
            break
        cursor = next_cursor

    return resources


def select_monitored_resources(
    services: list[dict[str, Any]],
    postgres: list[dict[str, Any]],
    disks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    selected_ids = configured_resource_ids()
    name_filter = settings.render_service_name_filter.strip().lower()
    disk_by_service = map_disks_to_services(disks)
    rows = [
        service_to_dashboard_row(service, disk_by_service.get(text_or_none(service.get("id")) or ""))
        for service in services
    ]
    rows.extend(postgres_to_dashboard_row(database) for database in postgres)

    if selected_ids:
        rows = [row for row in rows if row["id"] in selected_ids]
    elif name_filter:
        matched = [row for row in rows if name_filter in row["name"].lower()]
        rows = matched or rows

    return rows[:8]


def service_to_dashboard_row(service: dict[str, Any], disk: dict[str, Any] | None) -> dict[str, Any]:
    details = service.get("serviceDetails") if isinstance(service.get("serviceDetails"), dict) else {}
    return {
        "id": text_or_none(service.get("id")) or "",
        "name": text_or_none(service.get("name")) or "Render service",
        "type": humanise_type(text_or_none(service.get("type")) or text_or_none(details.get("type")) or "service"),
        "plan": text_or_none(service.get("plan")) or text_or_none(details.get("plan")) or "Not shown",
        "region": text_or_none(service.get("region")) or text_or_none(details.get("region")) or "Not shown",
        "runtime": text_or_none(service.get("runtime")) or text_or_none(details.get("runtime")) or "Not shown",
        "status": service_status(service),
        "url": text_or_none(service.get("serviceDetails", {}).get("url") if isinstance(service.get("serviceDetails"), dict) else None)
        or text_or_none(service.get("url")),
        "disk": disk_summary(disk),
        "metrics": {},
        "metric_errors": {},
    }


def postgres_to_dashboard_row(database: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": text_or_none(database.get("id")) or "",
        "name": text_or_none(database.get("name")) or "Render database",
        "type": "Postgres",
        "plan": text_or_none(database.get("plan")) or "Not shown",
        "region": text_or_none(database.get("region")) or "Not shown",
        "runtime": "PostgreSQL",
        "status": service_status(database),
        "url": None,
        "disk": None,
        "metrics": {},
        "metric_errors": {},
    }


def attach_metrics(client: httpx.Client, resources: list[dict[str, Any]]) -> None:
    for resource in resources:
        resource_id = text_or_none(resource.get("id"))
        if not resource_id:
            continue

        metric_params = metric_query_params([resource_id])
        for metric_name, endpoint in METRIC_ENDPOINTS.items():
            try:
                summaries = get_metric_summaries(client, endpoint, metric_params)
            except RenderUsageError as exc:
                resource["metric_errors"][metric_name] = str(exc)
                continue

            summary = summaries.get(resource_id) or first_metric_summary(summaries)
            if summary:
                resource["metrics"][metric_name] = summary

        add_usage_percent(resource, "cpu", "cpu_limit")
        add_usage_percent(resource, "memory", "memory_limit")
        add_usage_percent(resource, "disk_usage", "disk_capacity")


def first_metric_summary(summaries: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    return next(iter(summaries.values()), None)


def get_metric_summaries(client: httpx.Client, endpoint: str, params: list[tuple[str, Any]]) -> dict[str, dict[str, Any]]:
    payload = render_get(client, f"/metrics/{endpoint}", params=params)
    if not isinstance(payload, list):
        return {}

    grouped: dict[str, list[dict[str, Any]]] = {}
    fallback_resource_id = first_resource_id(params)
    for series in payload:
        if not isinstance(series, dict):
            continue
        resource_id = label_value(series, ("resource", "service", "postgres", "id")) or fallback_resource_id
        if not resource_id:
            continue
        grouped.setdefault(resource_id, []).append(series)

    return {resource_id: summarise_metric_series(series_rows) for resource_id, series_rows in grouped.items()}


def summarise_metric_series(series_rows: list[dict[str, Any]]) -> dict[str, Any]:
    values: list[tuple[datetime | None, float]] = []
    unit = None

    for series in series_rows:
        unit = unit or text_or_none(series.get("unit"))
        raw_values = series.get("values") or series.get("data") or []
        if not isinstance(raw_values, list):
            continue
        for raw_value in raw_values:
            timestamp = None
            value = None
            if isinstance(raw_value, dict):
                timestamp = parse_datetime(raw_value.get("timestamp") or raw_value.get("time"))
                value = numeric_value(raw_value.get("value"))
                unit = unit or text_or_none(raw_value.get("unit"))
            elif isinstance(raw_value, (list, tuple)) and len(raw_value) >= 2:
                timestamp = parse_datetime(raw_value[0])
                value = numeric_value(raw_value[1])
            else:
                value = numeric_value(raw_value)

            if value is not None:
                values.append((timestamp, value))

    if not values:
        return {"latest": None, "max": None, "average": None, "unit": unit, "points": 0}

    values.sort(key=lambda item: item[0] or datetime.min.replace(tzinfo=timezone.utc))
    numeric_values = [item[1] for item in values]
    return {
        "latest": round(values[-1][1], 3),
        "max": round(max(numeric_values), 3),
        "average": round(sum(numeric_values) / len(numeric_values), 3),
        "unit": unit,
        "points": len(values),
        "last_timestamp": values[-1][0].isoformat() if values[-1][0] else None,
    }


def metric_query_params(resource_ids: list[str]) -> list[tuple[str, Any]]:
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(minutes=safe_window_minutes())
    params: list[tuple[str, Any]] = [
        ("startTime", render_metric_timestamp(start_time)),
        ("endTime", render_metric_timestamp(end_time)),
        ("resolutionSeconds", 60),
    ]
    params.extend(("resource", resource_id) for resource_id in resource_ids)
    return params


def render_metric_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def render_get(client: httpx.Client, path: str, params: dict[str, Any] | list[tuple[str, Any]] | None = None) -> Any:
    try:
        response = client.get(path, params=params)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = response_error_detail(exc.response)
        raise RenderUsageError(f"Render returned {exc.response.status_code} for {path}: {detail}") from exc
    except httpx.HTTPError as exc:
        raise RenderUsageError(f"Render could not be reached: {exc}") from exc

    try:
        return response.json()
    except ValueError as exc:
        raise RenderUsageError("Render returned a response the portal could not read.") from exc


def response_error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text[:250]
    if isinstance(payload, dict):
        return text_or_none(payload.get("message") or payload.get("error")) or str(payload)[:250]
    return str(payload)[:250]


def build_render_summary(resources: list[dict[str, Any]]) -> dict[str, Any]:
    active_count = sum(1 for resource in resources if resource.get("status") in {"Live", "Available", "Healthy"})
    return {
        "monitored_services": len(resources),
        "active_services": active_count,
        "highest_cpu_percent": highest_percent(resources, "cpu_percent"),
        "highest_memory_percent": highest_percent(resources, "memory_percent"),
        "highest_disk_percent": highest_percent(resources, "disk_usage_percent"),
    }


def collect_metric_errors(resources: list[dict[str, Any]]) -> dict[str, str]:
    errors: dict[str, str] = {}
    for resource in resources:
        for metric_name, error in resource.get("metric_errors", {}).items():
            errors.setdefault(metric_name, error)
    return errors


def add_usage_percent(resource: dict[str, Any], usage_key: str, limit_key: str) -> None:
    usage = resource["metrics"].get(usage_key, {}).get("latest")
    limit = resource["metrics"].get(limit_key, {}).get("latest")
    if usage is None or limit in (None, 0):
        return
    resource["metrics"][f"{usage_key}_percent"] = round((usage / limit) * 100, 1)


def highest_percent(resources: list[dict[str, Any]], key: str) -> float | None:
    values = [
        numeric_value(resource.get("metrics", {}).get(key))
        for resource in resources
        if numeric_value(resource.get("metrics", {}).get(key)) is not None
    ]
    return max(values) if values else None


def map_disks_to_services(disks: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_service: dict[str, dict[str, Any]] = {}
    for disk in disks:
        service_id = text_or_none(disk.get("serviceId") or disk.get("serviceID"))
        if service_id:
            by_service[service_id] = disk
    return by_service


def disk_summary(disk: dict[str, Any] | None) -> dict[str, Any] | None:
    if not disk:
        return None
    return {
        "id": text_or_none(disk.get("id")),
        "name": text_or_none(disk.get("name")),
        "mount_path": text_or_none(disk.get("mountPath")),
        "size_gb": disk.get("sizeGB"),
    }


def configured_resource_ids() -> set[str]:
    return {
        item.strip()
        for item in settings.render_service_ids.split(",")
        if item.strip()
    }


def service_status(resource: dict[str, Any]) -> str:
    suspended = resource.get("suspended")
    if suspended in (True, "suspended", "true"):
        return "Suspended"
    status_value = text_or_none(resource.get("status") or resource.get("suspenders") or resource.get("state"))
    if status_value:
        return humanise_type(status_value)
    return "Live"


def label_value(series: dict[str, Any], label_names: tuple[str, ...]) -> str | None:
    labels = series.get("labels")
    if isinstance(labels, dict):
        for label_name in label_names:
            value = text_or_none(labels.get(label_name))
            if value:
                return value
    if isinstance(labels, list):
        for label in labels:
            if not isinstance(label, dict):
                continue
            key = text_or_none(label.get("key") or label.get("field") or label.get("name"))
            value = text_or_none(label.get("value"))
            if key in label_names and value:
                return value
    return None


def first_resource_id(params: list[tuple[str, Any]]) -> str | None:
    for key, value in params:
        if key == "resource":
            return text_or_none(value)
    return None


def parse_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def numeric_value(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def text_or_none(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def humanise_type(value: str) -> str:
    return value.replace("_", " ").replace("-", " ").title()


def safe_window_minutes() -> int:
    return max(5, min(settings.render_metrics_window_minutes, 24 * 60))
