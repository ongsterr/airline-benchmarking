import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
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
  overflowVisible?: boolean;
};

export function SectionCard({
  title,
  toolbar,
  children,
  overflowVisible,
}: SectionCardProps) {
  return (
    <Card className={cn(overflowVisible && "overflow-visible")}>
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
