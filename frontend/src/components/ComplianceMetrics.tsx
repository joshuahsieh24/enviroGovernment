import React from 'react';
import {
  Box,
  Grid,
  Typography,
  LinearProgress,
  Chip,
  Card,
  CardContent,
} from '@mui/material';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

const data = [
  { name: 'Environmental', value: 85, target: 100 },
  { name: 'Social', value: 72, target: 100 },
  { name: 'Governance', value: 91, target: 100 },
  { name: 'Reporting', value: 78, target: 100 },
];

const ComplianceMetrics: React.FC = () => {
  const metrics = [
    { name: 'ESRS E1 - Climate Change', progress: 85, status: 'On Track' },
    { name: 'ESRS E2 - Pollution', progress: 72, status: 'Needs Attention' },
    { name: 'ESRS E3 - Water & Marine', progress: 91, status: 'Excellent' },
    { name: 'ESRS S1 - Own Workforce', progress: 78, status: 'On Track' },
    { name: 'ESRS G1 - Business Conduct', progress: 88, status: 'Excellent' },
  ];

  return (
    <Box>
      {/* Chart */}
      <Box sx={{ mb: 4, height: 300 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="value" fill="#2e7d32" />
          </BarChart>
        </ResponsiveContainer>
      </Box>

      {/* Detailed Metrics */}
      <Grid container spacing={2}>
        {metrics.map((metric, index) => (
          <Grid item xs={12} key={index}>
            <Card variant="outlined">
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                  <Typography variant="body2" fontWeight="medium">
                    {metric.name}
                  </Typography>
                  <Chip 
                    label={metric.status} 
                    size="small"
                    color={
                      metric.status === 'Excellent' ? 'success' :
                      metric.status === 'On Track' ? 'primary' : 'warning'
                    }
                  />
                </Box>
                <LinearProgress 
                  variant="determinate" 
                  value={metric.progress} 
                  sx={{ height: 6, borderRadius: 3 }}
                />
                <Typography variant="caption" color="text.secondary">
                  {metric.progress}% complete
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
};

export default ComplianceMetrics; 