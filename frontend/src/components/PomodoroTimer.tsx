import { useEffect, useState, useRef } from 'react';

interface PomodoroTimerProps {
  session: {
    id: number;
    task_id?: number | null;
    started_at: string;
  };
  onComplete: (duration: number) => void;
  onCancel: () => void;
}

const POMODORO_DURATION = 25 * 60;

export default function PomodoroTimer({ session, onComplete, onCancel }: PomodoroTimerProps) {
  const [timeLeft, setTimeLeft] = useState(POMODORO_DURATION);
  const [isRunning, setIsRunning] = useState(true);
  const endTimeRef = useRef<number>(Date.now() + POMODORO_DURATION * 1000);
  const startTimeRef = useRef<number>(Date.now());
  const pausedTimeLeftRef = useRef<number>(POMODORO_DURATION);

  useEffect(() => {
    startTimeRef.current = Date.now();
    endTimeRef.current = Date.now() + POMODORO_DURATION * 1000;
    setTimeLeft(POMODORO_DURATION);
    setIsRunning(true);
  }, []);

  useEffect(() => {
    let interval: any = null;

    if (isRunning) {
      interval = setInterval(() => {
        const remaining = Math.max(0, Math.ceil((endTimeRef.current - Date.now()) / 1000));
        setTimeLeft(remaining);

        if (remaining <= 0) {
          clearInterval(interval);
          setIsRunning(false);
          const duration = Math.round((Date.now() - startTimeRef.current) / 1000 / 60);
          onComplete(Math.max(1, duration));
        }
      }, 500);
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isRunning, onComplete]);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const handlePause = () => {
    pausedTimeLeftRef.current = timeLeft;
    setIsRunning(false);
  };

  const handleResume = () => {
    endTimeRef.current = Date.now() + pausedTimeLeftRef.current * 1000;
    setIsRunning(true);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl p-8 max-w-md w-full text-center">
        <div className="mb-6">
          <p className="text-sm text-gray-500 mb-2">Sessão de Foco</p>
          <p className="font-medium text-gray-900">
            {session.task_id ? `Tarefa #${session.task_id}` : 'Sessão livre'}
          </p>
        </div>

        <div className="relative w-48 h-48 mx-auto mb-8">
          <svg className="w-full h-full transform -rotate-90">
            <circle
              cx="96"
              cy="96"
              r="88"
              fill="none"
              stroke="#e5e7eb"
              strokeWidth="8"
            />
            <circle
              cx="96"
              cy="96"
              r="88"
              fill="none"
              stroke="#3b82f6"
              strokeWidth="8"
              strokeDasharray={2 * Math.PI * 88}
              strokeDashoffset={2 * Math.PI * 88 * (1 - timeLeft / POMODORO_DURATION)}
              strokeLinecap="round"
              className="transition-all duration-500 ease-linear"
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-5xl font-mono font-bold text-gray-900">
              {formatTime(timeLeft)}
            </span>
          </div>
        </div>

        <div className="flex gap-3 justify-center">
          {isRunning ? (
            <button
              onClick={handlePause}
              className="px-6 py-3 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 font-medium"
            >
              Pausar
            </button>
          ) : (
            <button
              onClick={handleResume}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
            >
              Continuar
            </button>
          )}
          <button
            onClick={onCancel}
            className="px-6 py-3 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 font-medium"
          >
            Cancelar
          </button>
        </div>

        <p className="mt-4 text-sm text-gray-500">
          Mantenha o foco. A sessão conta XP apenas ao concluir.
        </p>
      </div>
    </div>
  );
}