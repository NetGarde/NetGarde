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
import AnalyticsIcon from '@mui/icons-material/Analytics';
import DevicesOtherIcon from '@mui/icons-material/DevicesOther';
import MapIcon from '@mui/icons-material/Map';
import './MenuContent.css';

const mainListItems = [
  { text: 'Home', icon: <HomeRoundedIcon />, path: '/', iconClass: 'homeIcon' },
];

const digitalTwinItems = [
  { text: 'Client map', icon: <MapIcon />, path: '/client-map', iconClass: 'clientMapIcon' },
  { text: 'Network map', icon: <HubIcon />, path: '/network-map', iconClass: 'networkMapIcon' },
];

const analyticsItems = [
  { text: 'Client profiles', icon: <DevicesOtherIcon />, path: '/client-profiles', iconClass: 'clientProfilesIcon' },
];

const secondaryListItems: typeof mainListItems = [];

interface MenuContentProps {
  open?: boolean;
}

export default function MenuContent({ open = true }: MenuContentProps) {
  const theme = useTheme();
  const location = useLocation();
  const [digitalTwinOpen, setDigitalTwinOpen] = useState(true);
  const [analyticsOpen, setAnalyticsOpen] = useState(false);
  const navItemSx = sidebarNavItemSx(theme);
  const nestedNavItemSx = sidebarNavItemSx(theme, true);
  const sectionSx = sidebarSectionButtonSx(theme);

  useEffect(() => {
    const hasSelectedChild = digitalTwinItems.some((item) => location.pathname === item.path);
    if (hasSelectedChild) {
      setDigitalTwinOpen(true);
    }
    const hasSelectedAnalytics = analyticsItems.some((item) => location.pathname === item.path);
    if (hasSelectedAnalytics) {
      setAnalyticsOpen(true);
    }
  }, [location.pathname]);

  const renderNavItem = (item: typeof mainListItems[0], index: number) => {
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

  const renderSectionItems = (items: typeof digitalTwinItems, nested = true) =>
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
              <ListItemButton onClick={() => setDigitalTwinOpen(!digitalTwinOpen)} sx={sectionSx}>
                <ListItemIcon className="menuIcon" sx={{ minWidth: 40, justifyContent: 'flex-start' }}>
                  <HubIcon />
                </ListItemIcon>
                <ListItemText
                  primary="Digital twin"
                  sx={{ color: 'text.secondary' }}
                  primaryTypographyProps={{ fontSize: '0.875rem', fontWeight: 400 }}
                />
                {digitalTwinOpen ? <ExpandLess /> : <ExpandMore />}
              </ListItemButton>
            </ListItem>
            <Collapse in={digitalTwinOpen} timeout="auto" unmountOnExit>
              <List component="div" disablePadding dense>
                {renderSectionItems(digitalTwinItems)}
              </List>
            </Collapse>
          </>
        )}

        {open && (
          <>
            <ListItem disablePadding sx={{ display: 'block' }}>
              <ListItemButton onClick={() => setAnalyticsOpen(!analyticsOpen)} sx={sectionSx}>
                <ListItemIcon className="menuIcon" sx={{ minWidth: 40, justifyContent: 'flex-start' }}>
                  <AnalyticsIcon />
                </ListItemIcon>
                <ListItemText
                  primary="Analytics"
                  sx={{ color: 'text.secondary' }}
                  primaryTypographyProps={{ fontSize: '0.875rem', fontWeight: 400 }}
                />
                {analyticsOpen ? <ExpandLess /> : <ExpandMore />}
              </ListItemButton>
            </ListItem>
            <Collapse in={analyticsOpen} timeout="auto" unmountOnExit>
              <List component="div" disablePadding dense>
                {renderSectionItems(analyticsItems)}
              </List>
            </Collapse>
          </>
        )}

        {!open && (
          <>
            {renderSectionItems(digitalTwinItems, false)}
            {renderSectionItems(analyticsItems, false)}
          </>
        )}
      </List>
      <List dense sx={{ px: 0 }}>
        {secondaryListItems.map((item, index) => renderNavItem(item, index))}
      </List>
    </Stack>
  );
}
