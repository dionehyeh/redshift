export function SourceNote({
  source,
  resolution,
}: {
  source: string;
  resolution?: string;
}) {
  return (
    <span className="text-[10px] text-slate-400 block font-mono">
      Source: {source} {resolution ? `(${resolution})` : ""}
    </span>
  );
}
