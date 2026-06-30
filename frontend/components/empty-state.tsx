import { SectionCard } from "@/components/section-card";

export function EmptyState({ message }: { message: string }) {
  return (
    <SectionCard>
      <p className="py-12 text-center text-sm text-muted-foreground">{message}</p>
    </SectionCard>
  );
}
