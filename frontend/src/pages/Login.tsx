import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { auth } from '../services/api';

export function Login() {
  const [isRegister, setIsRegister] = useState(false);
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    try {
      const fn = isRegister ? auth.register : auth.login;
      const payload = isRegister ? { username, email, password } : { username, password };
      const res = await fn(username, password);
      localStorage.setItem('token', res.data.access_token);
      navigate('/scanner');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Authentication failed');
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center">
      <div className="w-full max-w-md p-8">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-white">PerfectTrading</h1>
          <p className="text-gray-400 mt-2">Cryptocurrency Futures Trading Platform</p>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:border-blue-500 focus:outline-none"
              required
              minLength={3}
            />
          </div>
          {isRegister && (
            <div>
              <label className="block text-sm text-gray-400 mb-1">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:border-blue-500 focus:outline-none"
                required
              />
            </div>
          )}
          <div>
            <label className="block text-sm text-gray-400 mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:border-blue-500 focus:outline-none"
              required
              minLength={isRegister ? 8 : 1}
            />
          </div>
          {error && <p className="text-red-400 text-sm">{error}</p>}
          <button
            type="submit"
            className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
          >
            {isRegister ? 'Create Account' : 'Sign In'}
          </button>
          <button
            type="button"
            onClick={() => setIsRegister(!isRegister)}
            className="w-full text-gray-400 text-sm hover:text-white transition-colors"
          >
            {isRegister ? 'Already have an account? Sign in' : "Don't have an account? Register"}
          </button>
        </form>
      </div>
    </div>
  );
}
