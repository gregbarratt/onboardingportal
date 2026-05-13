export default function PlaceholderPage({ title, eyebrow = "Portal" }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-soft">
      <p className="text-sm font-semibold text-sea">{eyebrow}</p>
      <h1 className="mt-1 text-2xl font-bold text-ink">{title}</h1>
      <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
        This area is ready for the next build phase.
      </p>
    </section>
  );
}
