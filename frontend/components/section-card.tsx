import type { ReactNode } from "react";
import {
  Card,
  CardAction,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

type SectionCardProps = {
  title?: string;
  toolbar?: ReactNode;
  children: ReactNode;
};

export function SectionCard({ title, toolbar, children }: SectionCardProps) {
  return (
    <Card>
      {(title || toolbar) && (
        <CardHeader className="flex flex-row items-center justify-between border-b px-4 py-3">
          {title ? (
            <CardTitle className="text-sm font-medium">{title}</CardTitle>
          ) : (
            <span />
          )}
          {toolbar && <CardAction className="col-start-2">{toolbar}</CardAction>}
        </CardHeader>
      )}
      <CardContent className="px-0 pb-0">{children}</CardContent>
    </Card>
  );
}
