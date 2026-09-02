import { format, parseISO, startOfWeek, addDays } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import type { HeatmapDay } from '../types';

interface HeatmapProps {
  days: HeatmapDay[];
  loading?: boolean;
}

const LEVELS = ['bg-gray-100', 'bg-green-200', 'bg-green-400', 'bg-green-600'];

function levelFor(count: number): string {
  if (count <= 0) return LEVELS[0];
  if (count <= 2) return LEVELS[1];
  if (count <= 4) return LEVELS[2];
  return LEVELS[3];
}

export default function Heatmap({ days, loading }: HeatmapProps) {
  if (loading) {
    return (
      <div className="h-32 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-4 border-blue-500 border-t-transparent"></div>
      </div>
    );
  }

  if (!days.length) return null;

  const firstDate = startOfWeek(parseISO(days[0].date), { weekStartsOn: 0 });
  const activeTotal = days.filter((d) => d.count > 0).length;
  const goalDays = days.filter((d) => d.minutes >= 50).length;

  const weeks: { label: string; cells: (HeatmapDay | null)[] }[] = [];
  let cursor = firstDate;
  const lastDate = parseISO(days[days.length - 1].date);
  const byDate = new Map(days.map((d) => [d.date, d]));

  while (cursor <= lastDate) {
    const cells: (HeatmapDay | null)[] = [];
    for (let i = 0; i < 7; i++) {
      const day = addDays(cursor, i);
      const key = format(day, 'yyyy-MM-dd');
      cells.push(byDate.get(key) ?? null);
    }
    weeks.push({ label: format(cursor, 'dd MMM', { locale: ptBR }), cells });
    cursor = addDays(cursor, 7);
  }

  return (
    <div>
      <div className="overflow-x-auto">
        <div className="inline-flex gap-1 min-w-max">
          {weeks.map((week, wi) => (
            <div key={wi} className="flex flex-col gap-1">
              <span className="text-[10px] text-gray-400 h-4 truncate">
                {wi % 2 === 0 ? week.label : ''}
              </span>
              {week.cells.map((day, di) => (
                <div
                  key={day?.date ?? `${wi}-${di}`}
                  title={
                    day
                      ? `${format(parseISO(day.date), "dd 'de' MMMM 'de' yyyy", { locale: ptBR })} — ${day.count} atividade(s), ${day.minutes} min`
                      : undefined
                  }
                  className={`w-3.5 h-3.5 rounded-sm ${
                    day ? levelFor(day.count) : 'bg-transparent'
                  } ${day && day.minutes >= 50 ? 'ring-1 ring-blue-500' : ''}`}
                />
              ))}
            </div>
          ))}
        </div>
      </div>
      <div className="mt-4 flex items-center justify-between text-xs text-gray-500">
        <span>
          {activeTotal} dias ativos · {goalDays} com meta batida (≥50 min)
        </span>
        <div className="flex items-center gap-1">
          <span>Menos</span>
          {LEVELS.map((level) => (
            <span key={level} className={`w-3 h-3 rounded-sm ${level}`}></span>
          ))}
          <span>Mais</span>
        </div>
      </div>
    </div>
  );
}
