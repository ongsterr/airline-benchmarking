export function PageFallback({ message }: { message: string }) {
  return (
    <p className="text-xs text-muted-foreground">{message}</p>
  );
}
