import { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { authApi } from '../lib/api';
import { useAuthStore } from '../hooks/useAuthStore';

export default function AuthCallback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { setAuth } = useAuthStore();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const authError = searchParams.get('error');
    const accessToken = searchParams.get('access_token');
    const refreshToken = searchParams.get('refresh_token');

    if (authError) {
      setError(authError);
      return;
    }
    if (!accessToken || !refreshToken) {
      setError('Resposta de autenticação inválida');
      return;
    }

    const complete = async () => {
      try {
        const tokens = {
          access_token: accessToken,
          refresh_token: refreshToken,
          token_type: 'bearer',
        };
        const response = await authApi.me();
        setAuth(response.data, tokens);
        navigate('/', { replace: true });
      } catch {
        setError('Falha ao concluir o login com GitHub');
      }
    };
    complete();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
        <div className="max-w-md w-full bg-white p-8 rounded-lg shadow-sm text-center">
          <h2 className="text-xl font-bold text-gray-900 mb-2">Falha no login com GitHub</h2>
          <p className="text-sm text-red-600 mb-6" role="alert">{error}</p>
          <Link to="/login" className="text-blue-600 hover:text-blue-500 font-medium">
            Voltar para o login
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-500 border-t-transparent mx-auto"></div>
        <p className="mt-4 text-sm text-gray-600">Concluindo login com GitHub...</p>
      </div>
    </div>
  );
}
