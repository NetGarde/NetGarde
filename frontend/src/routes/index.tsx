import { RouteObject } from 'react-router-dom';
import Layout from '../shared/components/Layout';
import DashboardPage from '../pages/DashboardPage';
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
    path: '/network-map',
    element: (
      <Layout>
        <NetworkMapPage />
      </Layout>
    ),
  },
];
