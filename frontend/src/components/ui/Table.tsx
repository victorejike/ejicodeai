import { ReactNode } from 'react';
import { cx } from './cx';

export interface Column<T> {
  key: string;
  header: ReactNode;
  /** Cell renderer. Return `null` and the table prints an em dash. */
  render: (row: T, index: number) => ReactNode;
  align?: 'left' | 'right' | 'center';
  width?: string;
  /** Hide on narrow screens instead of squeezing every column in. */
  hideBelow?: 'sm' | 'md' | 'lg';
  className?: string;
}

const ALIGN = {
  left: 'text-left',
  right: 'text-right',
  center: 'text-center',
} as const;

const HIDE = {
  sm: 'hidden sm:table-cell',
  md: 'hidden md:table-cell',
  lg: 'hidden lg:table-cell',
} as const;

export interface TableProps<T> {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T, index: number) => string;
  onRowClick?: (row: T, index: number) => void;
  /** Shown in place of the body when `rows` is empty. */
  empty?: ReactNode;
  loading?: boolean;
  loadingRows?: number;
  className?: string;
}

export function Table<T>({
  columns,
  rows,
  rowKey,
  onRowClick,
  empty,
  loading = false,
  loadingRows = 4,
  className,
}: TableProps<T>) {
  if (!loading && rows.length === 0 && empty) {
    return <>{empty}</>;
  }

  return (
    <div className={cx('w-full overflow-x-auto', className)}>
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-[var(--border)]">
            {columns.map((col) => (
              <th
                key={col.key}
                scope="col"
                style={col.width ? { width: col.width } : undefined}
                className={cx(
                  'px-3 py-2.5 text-[11px] font-semibold uppercase tracking-wider text-[var(--text-muted)]',
                  ALIGN[col.align ?? 'left'],
                  col.hideBelow && HIDE[col.hideBelow]
                )}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {loading
            ? Array.from({ length: loadingRows }).map((_, i) => (
                <tr key={`skeleton-${i}`} className="border-b border-[var(--border)]">
                  {columns.map((col) => (
                    <td
                      key={col.key}
                      className={cx('px-3 py-3', col.hideBelow && HIDE[col.hideBelow])}
                    >
                      <span className="block h-4 w-full max-w-[180px] rounded skeleton-shimmer" />
                    </td>
                  ))}
                </tr>
              ))
            : rows.map((row, index) => (
                <tr
                  key={rowKey(row, index)}
                  onClick={onRowClick ? () => onRowClick(row, index) : undefined}
                  className={cx(
                    'border-b border-[var(--border)] transition-colors last:border-0',
                    onRowClick && 'cursor-pointer hover:bg-[var(--glass-hover-bg)]'
                  )}
                >
                  {columns.map((col) => {
                    const cell = col.render(row, index);
                    const blank = cell === null || cell === undefined || cell === '';
                    return (
                      <td
                        key={col.key}
                        className={cx(
                          'px-3 py-3 align-middle',
                          ALIGN[col.align ?? 'left'],
                          blank && 'text-[var(--text-muted)]',
                          col.hideBelow && HIDE[col.hideBelow],
                          col.className
                        )}
                      >
                        {blank ? '—' : cell}
                      </td>
                    );
                  })}
                </tr>
              ))}
        </tbody>
      </table>
    </div>
  );
}

export default Table;
