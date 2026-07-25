import { useParams } from 'react-router-dom';
import AgentDetail from '../features/agents/AgentDetail';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';

export default function AgentDetailPage() {
  const { agentId } = useParams<{ agentId: string }>();
  if (!agentId) {
    return (
      <Box sx={{ p: 2 }}>
        <Alert severity="error">Missing agent id</Alert>
      </Box>
    );
  }
  return <AgentDetail agentId={agentId} />;
}
