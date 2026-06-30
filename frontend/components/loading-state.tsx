import { TableCell, TableRow } from "@/components/ui/table";

export function LoadingState({
  colSpan,
  message = "Loading...",
}: {
  colSpan: number;
  message?: string;
}) {
  return (
    <TableRow>
      <TableCell
        colSpan={colSpan}
        className="py-8 text-center text-xs text-muted-foreground"
      >
        {message}
      </TableCell>
    </TableRow>
  );
}

export function EmptyTableRow({
  colSpan,
  message,
}: {
  colSpan: number;
  message: string;
}) {
  return (
    <TableRow>
      <TableCell
        colSpan={colSpan}
        className="py-12 text-center text-sm text-muted-foreground"
      >
        {message}
      </TableCell>
    </TableRow>
  );
}
