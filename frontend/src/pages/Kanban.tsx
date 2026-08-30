import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { tasksApi, sessionsApi, journalApi } from '../lib/api';
import type { Task, StudySession, TaskStatus } from '../types';
import PomodoroTimer from '../components/PomodoroTimer';
import JournalModal from '../components/JournalModal';

const COLUMNS: { id: TaskStatus; title: string; color: string }[] = [
  { id: 'backlog', title: 'Backlog', color: 'bg-gray-100' },
  { id: 'today', title: 'Hoje', color: 'bg-blue-100' },
  { id: 'doing', title: 'Fazendo', color: 'bg-yellow-100' },
  { id: 'done', title: 'Feito', color: 'bg-green-100' },
];

interface SortableTaskProps {
  task: Task;
  onStartSession: (task: Task) => void;
  onMoveStatus: (task: Task, nextStatus: TaskStatus) => void;
  onDelete: (id: number) => void;
}

function SortableTask({ task, onStartSession, onMoveStatus, onDelete }: SortableTaskProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: task.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const nextStatuses: Record<TaskStatus, TaskStatus[]> = {
    backlog: ['today', 'doing'],
    today: ['doing', 'done'],
    doing: ['done', 'backlog'],
    done: ['backlog'],
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`bg-white rounded-lg shadow-sm p-4 mb-3 border border-gray-200 ${
        isDragging ? 'shadow-lg ring-2 ring-blue-500' : ''
      }`}
    >
      <div {...attributes} {...listeners} className="cursor-grab mb-2">
        <h4 className="font-medium text-gray-900">{task.title}</h4>
        {task.description && (
          <p className="text-sm text-gray-500 mt-1 line-clamp-2">{task.description}</p>
        )}
      </div>

      <div className="flex items-center justify-between mt-3 pt-2 border-t border-gray-100 text-xs">
        <div className="flex gap-1 flex-wrap">
          {nextStatuses[task.status].map((st) => (
            <button
              key={st}
              onClick={() => onMoveStatus(task, st)}
              className="px-2 py-0.5 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded font-medium capitalize"
            >
              → {st}
            </button>
          ))}
        </div>
        <div className="flex gap-2">
          {task.status !== 'done' && (
            <button
              onClick={() => onStartSession(task)}
              title="Focar com Pomodoro"
              className="px-2 py-0.5 bg-blue-50 text-blue-600 hover:bg-blue-100 rounded font-medium"
            >
              ⏱️ Focar
            </button>
          )}
          <button
            onClick={() => onDelete(task.id)}
            title="Excluir"
            className="text-gray-400 hover:text-red-500"
          >
            ✕
          </button>
        </div>
      </div>
    </div>
  );
}

function Column({
  tasks,
  status,
  onStartSession,
  onMoveStatus,
  onDelete,
}: {
  tasks: Task[];
  status: TaskStatus;
  onStartSession: (task: Task) => void;
  onMoveStatus: (task: Task, nextStatus: TaskStatus) => void;
  onDelete: (id: number) => void;
}) {
  const columnConfig = COLUMNS.find((c) => c.id === status)!;

  return (
    <div className={`flex-1 min-w-[280px] ${columnConfig.color} rounded-lg p-3 flex flex-col`}>
      <h3 className="font-semibold text-gray-700 mb-3 flex items-center justify-between">
        <span>{columnConfig.title}</span>
        <span className="text-xs bg-white bg-opacity-70 px-2 py-0.5 rounded-full text-gray-600">
          {tasks.length}
        </span>
      </h3>
      <SortableContext
        items={tasks.map((t) => t.id)}
        strategy={verticalListSortingStrategy}
      >
        <div className="flex-1">
          {tasks.map((task) => (
            <SortableTask
              key={task.id}
              task={task}
              onStartSession={onStartSession}
              onMoveStatus={onMoveStatus}
              onDelete={onDelete}
            />
          ))}
          {tasks.length === 0 && (
            <div className="text-center text-gray-400 py-8 text-sm border-2 border-dashed border-gray-200 rounded-lg">
              Nenhuma tarefa
            </div>
          )}
        </div>
      </SortableContext>
    </div>
  );
}

export default function Kanban() {
  const queryClient = useQueryClient();
  const [activeSession, setActiveSession] = useState<StudySession | null>(null);
  const [journalSessionId, setJournalSessionId] = useState<number | null>(null);

  const { data: tasks = [], isLoading, refetch } = useQuery<Task[]>({
    queryKey: ['tasks'],
    queryFn: async () => (await tasksApi.list()).data,
  });

  const createTaskMutation = useMutation({
    mutationFn: (data: { title: string; description?: string }) => tasksApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
  });

  const updateTaskMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Task> }) => tasksApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });

  const deleteTaskMutation = useMutation({
    mutationFn: (id: number) => tasksApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
  });

  const startSessionMutation = useMutation({
    mutationFn: (taskId?: number) => sessionsApi.start({ task_id: taskId }),
    onSuccess: (response) => {
      setActiveSession(response.data);
    },
  });

  const completeSessionMutation = useMutation({
    mutationFn: ({ id, duration }: { id: number; duration: number }) =>
      sessionsApi.complete(id, duration),
    onSuccess: () => {
      setActiveSession(null);
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    const activeTask = tasks.find((t) => t.id === active.id);
    const overTask = tasks.find((t) => t.id === over.id);

    if (!activeTask || !overTask) return;

    if (activeTask.status === overTask.status) {
      const colTasks = tasks.filter((t) => t.status === activeTask.status);
      const oldIndex = colTasks.findIndex((t) => t.id === active.id);
      const newIndex = colTasks.findIndex((t) => t.id === over.id);
      const reordered = arrayMove(colTasks, oldIndex, newIndex);

      await tasksApi.reorder(activeTask.status, reordered.map((t) => t.id));
    } else {
      await updateTaskMutation.mutateAsync({
        id: activeTask.id,
        data: { status: overTask.status },
      });
    }

    refetch();
  };

  const handleCompleteSession = (duration: number) => {
    if (activeSession) {
      completeSessionMutation.mutate({ id: activeSession.id, duration });
      setJournalSessionId(activeSession.id);
    }
  };

  const handleJournalSubmit = async (content: string) => {
    if (journalSessionId) {
      await journalApi.create({ session_id: journalSessionId, content });
      setJournalSessionId(null);
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    }
  };

  const handleMoveStatus = (task: Task, nextStatus: TaskStatus) => {
    updateTaskMutation.mutate({ id: task.id, data: { status: nextStatus } });
  };

  const groupedTasks = COLUMNS.reduce((acc, col) => {
    acc[col.id] = (Array.isArray(tasks) ? tasks : [])
      .filter((t) => t.status === col.id)
      .sort((a, b) => a.position - b.position);
    return acc;
  }, {} as Record<TaskStatus, Task[]>);

  const [newTaskTitle, setNewTaskTitle] = useState('');
  const [newTaskDesc, setNewTaskDesc] = useState('');
  const [showNewTask, setShowNewTask] = useState(false);

  const handleCreateTask = () => {
    if (newTaskTitle.trim()) {
      createTaskMutation.mutate({ title: newTaskTitle, description: newTaskDesc });
      setNewTaskTitle('');
      setNewTaskDesc('');
      setShowNewTask(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-500 border-t-transparent"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-4">
              <h1 className="text-xl font-bold text-gray-900">FlowState</h1>
              <span className="px-3 py-1 text-sm bg-blue-100 text-blue-800 rounded-full">Kanban</span>
            </div>
            <a href="/" className="text-sm text-gray-500 hover:text-gray-700">Dashboard</a>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-6 flex items-center justify-between">
          <h2 className="text-2xl font-bold text-gray-900">Quadro de Tarefas</h2>
          <button
            onClick={() => setShowNewTask(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium"
          >
            + Nova Tarefa
          </button>
        </div>

        {showNewTask && (
          <div className="bg-white rounded-lg shadow-sm p-4 mb-6">
            <div className="space-y-3">
              <input
                type="text"
                value={newTaskTitle}
                onChange={(e) => setNewTaskTitle(e.target.value)}
                placeholder="Título da tarefa"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                autoFocus
              />
              <textarea
                value={newTaskDesc}
                onChange={(e) => setNewTaskDesc(e.target.value)}
                placeholder="Descrição (opcional)"
                rows={2}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <div className="flex justify-end space-x-2">
                <button
                  onClick={() => setShowNewTask(false)}
                  className="px-4 py-2 text-gray-600 hover:text-gray-800"
                >
                  Cancelar
                </button>
                <button
                  onClick={handleCreateTask}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  Criar
                </button>
              </div>
            </div>
          </div>
        )}

        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragEnd={handleDragEnd}
        >
          <div className="flex gap-4 overflow-x-auto pb-4">
            {COLUMNS.map((col) => (
              <Column
                key={col.id}
                tasks={groupedTasks[col.id]}
                status={col.id}
                onStartSession={(task) => startSessionMutation.mutate(task.id)}
                onMoveStatus={handleMoveStatus}
                onDelete={(id) => deleteTaskMutation.mutate(id)}
              />
            ))}
          </div>
        </DndContext>

        {activeSession && (
          <PomodoroTimer
            session={activeSession}
            onComplete={handleCompleteSession}
            onCancel={() => setActiveSession(null)}
          />
        )}

        {journalSessionId && (
          <JournalModal
            sessionId={journalSessionId}
            onSubmit={handleJournalSubmit}
            onClose={() => setJournalSessionId(null)}
          />
        )}
      </main>
    </div>
  );
}