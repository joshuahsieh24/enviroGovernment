import React from 'react';
import {
  Box,
  Typography,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Chip,
  Divider,
} from '@mui/material';
import {
  Warning as WarningIcon,
  Error as ErrorIcon,
  Info as InfoIcon,
  Schedule as ScheduleIcon,
} from '@mui/icons-material';

const AlertsPanel: React.FC = () => {
  const alerts = [
    {
      id: 1,
      type: 'warning',
      title: 'ESRS E2 Compliance Gap',
      message: 'Pollution metrics missing for Q3 2024',
      time: '2 hours ago',
      priority: 'High',
    },
    {
      id: 2,
      type: 'error',
      title: 'Document Expiry Alert',
      message: 'Sustainability report expires in 15 days',
      time: '1 day ago',
      priority: 'Critical',
    },
    {
      id: 3,
      type: 'info',
      title: 'New CSRD Requirement',
      message: 'ESRS S2 implementation due next month',
      time: '3 days ago',
      priority: 'Medium',
    },
  ];

  const getIcon = (type: string) => {
    switch (type) {
      case 'error':
        return <ErrorIcon color="error" />;
      case 'warning':
        return <WarningIcon color="warning" />;
      default:
        return <InfoIcon color="info" />;
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'Critical':
        return 'error';
      case 'High':
        return 'warning';
      default:
        return 'info';
    }
  };

  return (
    <Box>
      <List>
        {alerts.map((alert, index) => (
          <React.Fragment key={alert.id}>
            <ListItem alignItems="flex-start">
              <ListItemIcon>
                {getIcon(alert.type)}
              </ListItemIcon>
              <ListItemText
                primary={
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Typography variant="body2" fontWeight="medium">
                      {alert.title}
                    </Typography>
                    <Chip 
                      label={alert.priority} 
                      size="small"
                      color={getPriorityColor(alert.priority) as any}
                    />
                  </Box>
                }
                secondary={
                  <Box>
                    <Typography variant="body2" color="text.secondary">
                      {alert.message}
                    </Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
                      <ScheduleIcon sx={{ fontSize: 14, mr: 0.5 }} />
                      <Typography variant="caption" color="text.secondary">
                        {alert.time}
                      </Typography>
                    </Box>
                  </Box>
                }
              />
            </ListItem>
            {index < alerts.length - 1 && <Divider variant="inset" component="li" />}
          </React.Fragment>
        ))}
      </List>
    </Box>
  );
};

export default AlertsPanel; 