import { RouteObject } from 'react-router-dom';
import Layout from '../shared/components/Layout';
import DashboardPage from '../pages/DashboardPage';
import AgentsPage from '../pages/AgentsPage';
import AgentDetailPage from '../pages/AgentDetailPage';
import AgentFlowPage from '../pages/AgentFlowPage';
import AlertsPage from '../pages/AlertsPage';
import SettingsPage from '../pages/SettingsPage';

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
  {
    path: '/agents/:agentId',
    element: (
      <Layout>
        <AgentDetailPage />
      </Layout>
    ),
  },
  {
    path: '/how-it-works',
    element: (
      <Layout>
        <AgentFlowPage />
      </Layout>
    ),
  },
  {
    path: '/alerts',
    element: (
      <Layout>
        <AlertsPage />
      </Layout>
    ),
  },
  {
    path: '/settings',
    element: (
      <Layout>
        <SettingsPage />
      </Layout>
    ),
  },
];
