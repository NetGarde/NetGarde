import { RouteObject } from 'react-router-dom';
import Layout from '../shared/components/Layout';
import DashboardPage from '../pages/DashboardPage';
import AgentsPage from '../pages/AgentsPage';

export const routes: RouteObject[] = [
  {
    path: '/',
    element: (
      <Layout>
        <DashboardPage />
      </Layout>
    ),
  },
  {
    path: '/agents',
    element: (
      <Layout>
        <AgentsPage />
      </Layout>
    ),
  },
];
