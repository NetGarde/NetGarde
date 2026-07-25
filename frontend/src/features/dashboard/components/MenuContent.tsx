import { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useTheme } from '@mui/material/styles';
import { sidebarNavItemSx, sidebarSectionButtonSx } from '../../../shared/theme/navigationChrome';
import Box from '@mui/material/Box';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import Collapse from '@mui/material/Collapse';
import Stack from '@mui/material/Stack';
import Tooltip from '@mui/material/Tooltip';
import type { ReactElement } from 'react';
import ExpandLess from '@mui/icons-material/ExpandLess';
import ExpandMore from '@mui/icons-material/ExpandMore';
import HomeRoundedIcon from '@mui/icons-material/HomeRounded';
import DevicesOtherIcon from '@mui/icons-material/DevicesOther';
import NotificationImportantIcon from '@mui/icons-material/NotificationImportant';
import SettingsOutlinedIcon from '@mui/icons-material/SettingsOutlined';
import ComputerIcon from '@mui/icons-material/Computer';
import ShieldOutlinedIcon from '@mui/icons-material/ShieldOutlined';
import RouteOutlinedIcon from '@mui/icons-material/RouteOutlined';
import MenuBookOutlinedIcon from '@mui/icons-material/MenuBookOutlined';
import './MenuContent.css';

type NavItem = {
  text: string;
  icon: ReactElement;
  path: string;
  iconClass: string;
};

type NavSection = {
  id: string;
  label: string;
  icon: ReactElement;
  items: NavItem[];
};

const mainListItems: NavItem[] = [
  { text: 'Home', icon: <HomeRoundedIcon />, path: '/', iconClass: 'homeIcon' },
];

const navSections: NavSection[] = [
  {
    id: 'endpoints',
    label: 'Endpoints',
    icon: <ComputerIcon />,
    items: [
      {
        text: 'Agents',
        icon: <DevicesOtherIcon />,
        path: '/agents',
        iconClass: 'clientProfilesIcon',
      },
    ],
  },
  {
    id: 'detection',
    label: 'Detection',
    icon: <ShieldOutlinedIcon />,
    items: [
      {
        text: 'Alerts',
        icon: <NotificationImportantIcon />,
        path: '/alerts',
        iconClass: 'alertsIcon',
      },
    ],
  },
  {
    id: 'learn',
    label: 'Learn',
    icon: <MenuBookOutlinedIcon />,
    items: [
      {
        text: 'How it works',
        icon: <RouteOutlinedIcon />,
        path: '/how-it-works',
        iconClass: 'homeIcon',
      },
    ],
  },
];

const secondaryListItems: NavItem[] = [
  {
    text: 'Settings',
    icon: <SettingsOutlinedIcon />,
    path: '/settings',
    iconClass: 'settingsIcon',
  },
];

interface MenuContentProps {
  open?: boolean;
}

export default function MenuContent({ open = true }: MenuContentProps) {
  const theme = useTheme();
  const location = useLocation();
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({
    endpoints: true,
    detection: true,
    learn: true,
  });
  const navItemSx = sidebarNavItemSx(theme);
  const nestedNavItemSx = sidebarNavItemSx(theme, true);
  const sectionSx = sidebarSectionButtonSx(theme);

  useEffect(() => {
    setOpenSections((prev) => {
      const next = { ...prev };
      for (const section of navSections) {
        if (
          section.items.some(
            (item) =>
              location.pathname === item.path || location.pathname.startsWith(`${item.path}/`),
          )
        ) {
          next[section.id] = true;
        }
      }
      return next;
    });
  }, [location.pathname]);

  const toggleSection = (id: string) => {
    setOpenSections((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const renderNavItem = (item: NavItem, index: number, nested = false) => {
    const isSelected =
      item.path === '/'
        ? location.pathname === '/'
        : location.pathname === item.path || location.pathname.startsWith(`${item.path}/`);
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
  };

  return (
    <Stack sx={{ flexGrow: 1, p: 1, justifyContent: 'space-between' }}>
      <List dense sx={{ px: 0 }}>
        {mainListItems.map((item, index) => renderNavItem(item, index))}

        {open &&
          navSections.map((section) => (
            <Box key={section.id} component="div">
              <ListItem disablePadding sx={{ display: 'block' }}>
                <ListItemButton onClick={() => toggleSection(section.id)} sx={sectionSx}>
                  <ListItemIcon className="menuIcon" sx={{ minWidth: 40, justifyContent: 'flex-start' }}>
                    {section.icon}
                  </ListItemIcon>
                  <ListItemText
                    primary={section.label}
                    sx={{ color: 'text.secondary' }}
                    primaryTypographyProps={{ fontSize: '0.875rem', fontWeight: 400 }}
                  />
                  {openSections[section.id] ? <ExpandLess /> : <ExpandMore />}
                </ListItemButton>
              </ListItem>
              <Collapse in={!!openSections[section.id]} timeout="auto" unmountOnExit>
                <List component="div" disablePadding dense>
                  {section.items.map((item, index) => renderNavItem(item, index, true))}
                </List>
              </Collapse>
            </Box>
          ))}

        {!open &&
          navSections.flatMap((section) =>
            section.items.map((item, index) => renderNavItem(item, index, false)),
          )}
      </List>
      <List dense sx={{ px: 0 }}>
        {secondaryListItems.map((item, index) => renderNavItem(item, index))}
      </List>
    </Stack>
  );
}
