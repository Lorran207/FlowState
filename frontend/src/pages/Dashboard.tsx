import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { activityApi, dashboardApi, githubApi } from '../lib/api';
import { useAuthStore } from '../hooks/useAuthStore';
import type { DashboardData, FeedItem, GitHubStatus, HeatmapDay, SyncResult } from '../types';
import Heatmap from '../components/Heatmap';
import ActivityFeed from '../components/ActivityFeed';

export default function Dashboard() {
  const { user, accessToken, logout } = useAuthStore();
  const queryClient = useQueryClient();
  const [weeklyMinutes, setWeeklyMinutes] = useState(0);

  const { data, isLoading, error } = useQuery<DashboardData>({
    queryKey: ['dashboard'],
    queryFn: async () => (await dashboardApi.get()).data,
  });

  const { data: githubStatus } = useQuery<GitHubStatus>({
    queryKey: ['github-status'],
    queryFn: async () => (await githubApi.status()).data,
  });

  const { data: heatmapDays, isLoading: heatmapLoading } = useQuery<HeatmapDay[]>({
    queryKey: ['heatmap'],
    queryFn: async () => (await activityApi.heatmap(182)).data,
  });

  const { data: feedItems, isLoading: feedLoading } = useQuery<FeedItem[]>({
    queryKey: ['activity-feed'],
    queryFn: async () => (await activityApi.feed(14, 30)).data,
  });

  const syncMutation = useMutation<SyncResult>({
    mutationFn: async () => (await githubApi.sync()).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['github-status'] });
      queryClient.invalidateQueries({ queryKey: ['activity-feed'] });
      queryClient.invalidateQueries({ queryKey: ['heatmap'] });
    },
  });

  useEffect(() => {
    if (data) setWeeklyMinutes(data.weekly_minutes);
  }, [data]);

  const formatMinutes = (minutes: number) => {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return hours > 0 ? `${hours}h ${mins}min` : `${mins}min`;
  };

  const getLevelProgress = (xp: number) => {
    const xpPerLevel = 100;
    const currentLevelXp = xp % xpPerLevel;
    return (currentLevelXp / xpPerLevel) * 100;
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-500 border-t-transparent"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600">Erro ao carregar dashboard</p>
          <button onClick={logout} className="mt-4 text-blue-600 hover:underline">Sair</button>
        </div>
      </div>
    );
  }

  const stats = data?.stats;
  const progress = stats ? getLevelProgress(stats.xp_total) : 0;

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <h1 className="text-xl font-bold text-gray-900">FlowState</h1>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-700">{user?.name}</span>
              <button
                onClick={logout}
                className="text-sm text-gray-500 hover:text-gray-700"
              >
                Sair
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-gray-900">Dashboard</h2>
          <p className="text-gray-600 mt-1">Seu progresso de aprendizado</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow-sm p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-500">Nível</p>
                <p className="text-3xl font-bold text-gray-900">{stats?.level || 1}</p>
              </div>
              <div className="bg-blue-100 p-3 rounded-full">
                <svg className="h-6 w-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
            </div>
            <div className="mt-4">
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${progress}%` }}
                ></div>
              </div>
              <p className="text-xs text-gray-500 mt-1">{stats?.xp_total || 0} XP</p>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-sm p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-500">Streak</p>
                <p className="text-3xl font-bold text-gray-900">{stats?.streak || 0} dias</p>
              </div>
              <div className="bg-orange-100 p-3 rounded-full">
                <svg className="h-6 w-6 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 18.657A8 8 0 016.343 7.343S7 9 9 10c0-2 .5-5 2.986-7C14 5 16.09 5.777 17.656 7.343A7.975 7.975 0 0120 13a7.975 7.975 0 01-2.343 5.657z" />
                </svg>
              </div>
            </div>
            <p className="text-sm text-gray-500 mt-2">Maior: {stats?.longest_streak || 0} dias</p>
          </div>

          <div className="bg-white rounded-lg shadow-sm p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-500">Esta Semana</p>
                <p className="text-3xl font-bold text-gray-900">{formatMinutes(weeklyMinutes)}</p>
              </div>
              <div className="bg-green-100 p-3 rounded-full">
                <svg className="h-6 w-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
            </div>
            <p className="text-sm text-gray-500 mt-2">Minutos de foco</p>
          </div>

          <div className="bg-white rounded-lg shadow-sm p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-500">Total XP</p>
                <p className="text-3xl font-bold text-gray-900">{stats?.xp_total || 0}</p>
              </div>
              <div className="bg-purple-100 p-3 rounded-full">
                <svg className="h-6 w-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
              </div>
            </div>
            <p className="text-sm text-gray-500 mt-2">Próximo nível: {100 - ((stats?.xp_total ?? 0) % 100)} XP</p>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm p-6 mb-8">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="bg-gray-900 p-2 rounded-full">
                <svg className="h-6 w-6 text-white" fill="currentColor" viewBox="0 0 24 24">
                  <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd" />
                </svg>
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900">GitHub</h3>
                {githubStatus?.connected ? (
                  <p className="text-sm text-gray-500">
                    Conectado como <span className="font-medium text-gray-700">@{githubStatus.username}</span>
                    {' '}· {githubStatus.commit_count} commits rastreados
                  </p>
                ) : (
                  <p className="text-sm text-gray-500">
                    Conecte sua conta para transformar commits em evidência de estudo
                  </p>
                )}
              </div>
            </div>
            {githubStatus?.connected ? (
              <div className="flex items-center gap-3">
                {syncMutation.isSuccess && (
                  <span className="text-sm text-green-600">
                    +{syncMutation.data.new_commits} novos commits
                  </span>
                )}
                {syncMutation.isError && (
                  <span className="text-sm text-red-600">Falha ao sincronizar</span>
                )}
                <button
                  onClick={() => syncMutation.mutate()}
                  disabled={syncMutation.isPending}
                  className="px-4 py-2 bg-gray-900 text-white text-sm font-medium rounded-md hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {syncMutation.isPending ? 'Sincronizando...' : 'Sincronizar commits'}
                </button>
              </div>
            ) : (
              <a
                href={githubApi.authorizeUrl(accessToken)}
                className="px-4 py-2 bg-gray-900 text-white text-sm font-medium rounded-md hover:bg-gray-800 text-center"
              >
                Conectar GitHub
              </a>
            )}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm p-6 mb-8">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Mapa de Atividade</h3>
              <p className="text-sm text-gray-500">Pomodoros, journals e commits dos últimos 6 meses</p>
            </div>
          </div>
          <Heatmap days={heatmapDays ?? []} loading={heatmapLoading} />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow-sm p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">Sessões Recentes</h3>
              <Link to="/kanban" className="text-sm text-blue-600 hover:text-blue-500">Ver todas</Link>
            </div>
            <div className="space-y-3">
              {data?.recent_sessions.length === 0 ? (
                <p className="text-gray-500 text-center py-4">Nenhuma sessão ainda</p>
              ) : (
                data?.recent_sessions.map((session) => (
                  <div key={session.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div>
                      <p className="font-medium text-gray-900">
                        {session.task_id ? `Tarefa #${session.task_id}` : 'Sessão livre'}
                      </p>
                      <p className="text-sm text-gray-500">
                        {session.duration_min ? `${session.duration_min} min` : 'Em andamento'}
                      </p>
                    </div>
                    <span
                      className={`px-2 py-1 text-xs rounded-full ${
                        session.completed ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                      }`}
                    >
                      {session.completed ? 'Concluída' : 'Ativa'}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-sm p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">Em Progresso</h3>
              <Link to="/kanban" className="text-sm text-blue-600 hover:text-blue-500">Ver Kanban</Link>
            </div>
            <div className="space-y-3">
              {data?.recent_tasks.length === 0 ? (
                <p className="text-gray-500 text-center py-4">Nenhuma tarefa em andamento</p>
              ) : (
                data?.recent_tasks.map((task) => (
                  <div key={task.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div>
                      <p className="font-medium text-gray-900 truncate max-w-[200px]">{task.title}</p>
                      <p className="text-sm text-gray-500">Posição: {task.position + 1}</p>
                    </div>
                    <span className="px-2 py-1 text-xs rounded-full bg-blue-100 text-blue-800">Fazendo</span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm p-6 mb-8">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Feed de Atividades</h3>
              <p className="text-sm text-gray-500">Evidências de estudo: foco, registros e código</p>
            </div>
          </div>
          <ActivityFeed items={feedItems ?? []} loading={feedLoading} />
        </div>

        <div className="text-center">
          <Link
            to="/kanban"
            className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
          >
            <svg className="h-5 w-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
            </svg>
            Abrir Kanban
          </Link>
        </div>
      </main>
    </div>
  );
}