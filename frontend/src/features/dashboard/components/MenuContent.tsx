import { useState, useEffect } from 'react';
import { useLocation, Link } from 'react-router-dom';
import { useTheme } from '@mui/material/styles';
import { sidebarNavItemSx, sidebarSectionButtonSx } from '../../../shared/theme/navigationChrome';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import Collapse from '@mui/material/Collapse';
import Stack from '@mui/material/Stack';
import Tooltip from '@mui/material/Tooltip';
import ExpandLess from '@mui/icons-material/ExpandLess';
import ExpandMore from '@mui/icons-material/ExpandMore';
import HomeRoundedIcon from '@mui/icons-material/HomeRounded';
import HubIcon from '@mui/icons-material/Hub';
import DevicesOtherIcon from '@mui/icons-material/DevicesOther';
import './MenuContent.css';

const mainListItems = [
  { text: 'Home', icon: <HomeRoundedIcon />, path: '/', iconClass: 'homeIcon' },
];

const observabilityItems = [
  { text: 'Agents', icon: <DevicesOtherIcon />, path: '/agents', iconClass: 'clientProfilesIcon' },
];

const secondaryListItems: typeof mainListItems = [];

interface MenuContentProps {
  open?: boolean;
}

export default function MenuContent({ open = true }: MenuContentProps) {
  const theme = useTheme();
  const location = useLocation();
  const [observabilityOpen, setObservabilityOpen] = useState(true);
  const navItemSx = sidebarNavItemSx(theme);
  const nestedNavItemSx = sidebarNavItemSx(theme, true);
  const sectionSx = sidebarSectionButtonSx(theme);

  useEffect(() => {
    const hasSelectedChild = observabilityItems.some((item) => location.pathname === item.path);
    if (hasSelectedChild) {
      setObservabilityOpen(true);
    }
  }, [location.pathname]);

  const renderNavItem = (item: (typeof mainListItems)[0], index: number) => {
    const isSelected = location.pathname === item.path;
    const button = (
      <ListItemButton
        component={Link}
        to={item.path}
        selected={isSelected}
        className="azure-sidebar-item"
        sx={navItemSx}
      >
        <ListItemIcon
          className={`menuIcon ${item.iconClass}`}
          sx={{
            minWidth: open ? 40 : 'auto',
            justifyContent: open ? 'flex-start' : 'center',
          }}
        >
          {item.icon}
        </ListItemIcon>
        {open && (
          <ListItemText
            primary={item.text}
            sx={{ color: isSelected ? 'text.primary' : 'text.secondary' }}
            primaryTypographyProps={{
              fontSize: '0.875rem',
              fontWeight: isSelected ? 500 : 400,
            }}
          />
        )}
      </ListItemButton>
    );

    return (
      <ListItem key={index} disablePadding sx={{ display: 'block' }}>
        {!open ? (
          <Tooltip title={item.text} placement="right" arrow>
            <span>{button}</span>
          </Tooltip>
        ) : (
          button
        )}
      </ListItem>
    );
  };

  const renderSectionItems = (items: typeof observabilityItems, nested = true) =>
    items.map((item, index) => {
      const isSelected = location.pathname === item.path;
      const button = (
        <ListItemButton
          component={Link}
          to={item.path}
          selected={isSelected}
          className="azure-sidebar-item"
          sx={nested ? nestedNavItemSx : navItemSx}
        >
          <ListItemIcon
            className={`menuIcon ${item.iconClass}`}
            sx={{
              minWidth: open ? 40 : 'auto',
              justifyContent: open ? 'flex-start' : 'center',
            }}
          >
            {item.icon}
          </ListItemIcon>
          {open && (
            <ListItemText
              primary={item.text}
              sx={{ color: isSelected ? 'text.primary' : 'text.secondary' }}
              primaryTypographyProps={{
                fontSize: '0.875rem',
                fontWeight: isSelected ? 500 : 400,
              }}
            />
          )}
        </ListItemButton>
      );

      return (
        <ListItem key={`${item.path}-${index}`} disablePadding sx={{ display: 'block' }}>
          {!open ? (
            <Tooltip title={item.text} placement="right" arrow>
              <span>{button}</span>
            </Tooltip>
          ) : (
            button
          )}
        </ListItem>
      );
    });

  return (
    <Stack sx={{ flexGrow: 1, p: 1, justifyContent: 'space-between' }}>
      <List dense sx={{ px: 0 }}>
        {mainListItems.map((item, index) => renderNavItem(item, index))}

        {open && (
          <>
            <ListItem disablePadding sx={{ display: 'block' }}>
              <ListItemButton onClick={() => setObservabilityOpen(!observabilityOpen)} sx={sectionSx}>
                <ListItemIcon className="menuIcon" sx={{ minWidth: 40, justifyContent: 'flex-start' }}>
                  <HubIcon />
                </ListItemIcon>
                <ListItemText
                  primary="Observability"
                  sx={{ color: 'text.secondary' }}
                  primaryTypographyProps={{ fontSize: '0.875rem', fontWeight: 400 }}
                />
                {observabilityOpen ? <ExpandLess /> : <ExpandMore />}
              </ListItemButton>
            </ListItem>
            <Collapse in={observabilityOpen} timeout="auto" unmountOnExit>
              <List component="div" disablePadding dense>
                {renderSectionItems(observabilityItems)}
              </List>
            </Collapse>
          </>
        )}

        {!open && renderSectionItems(observabilityItems, false)}
      </List>
      <List dense sx={{ px: 0 }}>
        {secondaryListItems.map((item, index) => renderNavItem(item, index))}
      </List>
    </Stack>
  );
}
