import { useMemo } from 'react';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Chip from '@mui/material/Chip';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import { DestinationRow } from '../utils/buildDestinationRows';

interface DestinationTableProps {
  rows: DestinationRow[];
  selectedRowId: string | null;
  onSelectRow: (row: DestinationRow) => void;
}

interface ClientGroup {
  clientId: string;
  clientLabel: string;
  clientIp: string | null;
  source: DestinationRow['source'];
  rows: DestinationRow[];
}

function groupRowsByClient(rows: DestinationRow[]): ClientGroup[] {
  const groups: ClientGroup[] = [];
  const indexByClient = new Map<string, number>();
  for (const row of rows) {
    let idx = indexByClient.get(row.clientId);
    if (idx == null) {
      idx = groups.length;
      indexByClient.set(row.clientId, idx);
      groups.push({
        clientId: row.clientId,
        clientLabel: row.clientLabel,
        clientIp: row.clientIp,
        source: row.source,
        rows: [],
      });
    }
    groups[idx].rows.push(row);
  }
  return groups;
}

export default function DestinationTable({
  rows,
  selectedRowId,
  onSelectRow,
}: DestinationTableProps) {
  const groups = useMemo(() => groupRowsByClient(rows), [rows]);

  if (rows.length === 0) {
    return (
      <Box sx={{ py: 3, px: 1 }}>
        <Typography variant="body2" color="text.secondary">
          No destinations in the current window. Seed demo data or wait for live DNS/flows.
        </Typography>
      </Box>
    );
  }

  return (
    <TableContainer sx={{ maxHeight: 420 }}>
      <Table size="small" stickyHeader aria-label="Who talked to what">
        <TableHead>
          <TableRow>
            <TableCell>Process</TableCell>
            <TableCell>Destination</TableCell>
            <TableCell>Port</TableCell>
            <TableCell>Action</TableCell>
            <TableCell align="right">Count</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {groups.map((group) => (
            <ClientGroupRows
              key={group.clientId}
              group={group}
              selectedRowId={selectedRowId}
              onSelectRow={onSelectRow}
            />
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}

function ClientGroupRows({
  group,
  selectedRowId,
  onSelectRow,
}: {
  group: ClientGroup;
  selectedRowId: string | null;
  onSelectRow: (row: DestinationRow) => void;
}) {
  return (
    <>
      <TableRow
        sx={{
          bgcolor: (theme) =>
            theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.04)',
        }}
      >
        <TableCell colSpan={5} sx={{ py: 1 }}>
          <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
            <Typography variant="subtitle2" fontWeight={700}>
              {group.clientLabel}
            </Typography>
            {group.clientIp && (
              <Typography variant="caption" color="text.secondary" sx={{ fontFamily: 'ui-monospace, monospace' }}>
                {group.clientIp}
              </Typography>
            )}
            <Chip
              size="small"
              label={group.source === 'vpn' ? 'Endpoint' : 'Agent'}
              variant="outlined"
              sx={{ height: 20, fontSize: 11 }}
            />
            <Typography variant="caption" color="text.secondary">
              {group.rows.length} destination{group.rows.length === 1 ? '' : 's'}
            </Typography>
          </Stack>
        </TableCell>
      </TableRow>
      {group.rows.map((row) => {
        const selected = row.id === selectedRowId;
        return (
          <TableRow
            key={row.id}
            hover
            selected={selected}
            onClick={() => onSelectRow(row)}
            sx={{ cursor: 'pointer' }}
          >
            <TableCell>
              <Typography variant="body2" fontWeight={500}>
                {row.appLabel ?? '—'}
              </Typography>
            </TableCell>
            <TableCell>
              <Typography
                variant="body2"
                sx={{
                  fontFamily: row.destinationKind === 'domain' ? undefined : 'ui-monospace, monospace',
                  fontSize: row.destinationKind === 'domain' ? undefined : 12,
                }}
              >
                {row.destination}
              </Typography>
            </TableCell>
            <TableCell sx={{ fontFamily: 'ui-monospace, monospace', fontSize: 12 }}>
              {row.port ? `:${row.port}` : '—'}
            </TableCell>
            <TableCell>
              <Chip
                size="small"
                label={row.action}
                color={row.action === 'block' ? 'error' : 'default'}
                variant={row.action === 'block' ? 'filled' : 'outlined'}
                sx={{ height: 22, textTransform: 'uppercase', fontSize: 11 }}
              />
            </TableCell>
            <TableCell align="right">{row.queryCount}</TableCell>
          </TableRow>
        );
      })}
    </>
  );
}
