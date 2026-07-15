import { FormEvent, useState } from 'react';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import CircularProgress from '@mui/material/CircularProgress';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import { parseSimulationCommand, SimulationCommandResponse } from '../../twin-graph/api/twinGraphApi';

interface SimulationCommandBarProps {
  activePorts: number[];
  activeApps: string[];
  onCommand: (response: SimulationCommandResponse) => void;
}

export default function SimulationCommandBar({
  activePorts,
  activeApps,
  onCommand,
}: SimulationCommandBarProps) {
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState<{ message: string; source: string } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    const trimmed = prompt.trim();
    if (!trimmed) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await parseSimulationCommand({
        prompt: trimmed,
        active_ports: activePorts,
        active_apps: activeApps,
      });
      setFeedback({ message: response.message, source: response.source });
      onCommand(response);
      if (response.action !== 'unknown' && response.action !== 'noop') {
        setPrompt('');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Command failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{ mb: 1.5 }}>
      <Stack component="form" direction={{ xs: 'column', sm: 'row' }} spacing={1} onSubmit={handleSubmit}>
        <TextField
          size="small"
          fullWidth
          placeholder='Try "block wireguard", "block port 443", or "clear simulation"'
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          disabled={loading}
          InputProps={{
            startAdornment: <AutoAwesomeIcon sx={{ fontSize: 18, mr: 1, color: 'text.secondary' }} />,
          }}
        />
        <Button type="submit" variant="outlined" disabled={loading || !prompt.trim()} sx={{ whiteSpace: 'nowrap' }}>
          {loading ? <CircularProgress size={18} /> : 'Run'}
        </Button>
      </Stack>
      <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
        Natural-language what-if via Ollama (rules parser first). Example: block wireguard, block https, clear.
      </Typography>
      {feedback && (
        <Alert severity="success" sx={{ mt: 1 }} onClose={() => setFeedback(null)}>
          {feedback.message}
          {feedback.source === 'ollama' && ' · parsed by Ollama'}
        </Alert>
      )}
      {error && (
        <Alert severity="error" sx={{ mt: 1 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
    </Box>
  );
}
