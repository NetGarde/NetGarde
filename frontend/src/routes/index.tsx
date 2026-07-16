import { RouteObject } from 'react-router-dom';
import Layout from '../shared/components/Layout';
import DashboardPage from '../pages/DashboardPage';
import ClientProfilesPage from '../pages/ClientProfilesPage';
import NetworkMapPage from '../pages/NetworkMapPage';

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
    path: '/client-profiles',
    element: (
      <Layout>
        <ClientProfilesPage />
      </Layout>
    ),
  },
  {
    path: '/network-map',
    element: (
      <Layout>
        <NetworkMapPage />
      </Layout>
    ),
  },
];
