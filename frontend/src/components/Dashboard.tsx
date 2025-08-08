import React from 'react';
import {
  Grid,
  Paper,
  Typography,
  Box,
  Card,
  CardContent,
  CardActions,
  Button,
  LinearProgress,
  Chip,
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  Upload as UploadIcon,
} from '@mui/icons-material';
import ComplianceMetrics from './ComplianceMetrics';
import DataUpload from './DataUpload';
import AlertsPanel from './AlertsPanel';

const Dashboard: React.FC = () => {
  const complianceScore = 87;
  const documentsProcessed = 156;
  const alertsCount = 3;
  const gapsIdentified = 12;

  return (
    <Box>
      {/* Welcome Section */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom>
          Welcome to ESG Insight Hub
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Monitor your sustainability compliance, track CSRD metrics, and manage ESG reporting.
        </Typography>
      </Box>

      {/* Key Metrics */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <CheckCircleIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6">Compliance Score</Typography>
              </Box>
              <Typography variant="h3" color="primary" gutterBottom>
                {complianceScore}%
              </Typography>
              <LinearProgress 
                variant="determinate" 
                value={complianceScore} 
                sx={{ height: 8, borderRadius: 4 }}
              />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <UploadIcon color="secondary" sx={{ mr: 1 }} />
                <Typography variant="h6">Documents Processed</Typography>
              </Box>
              <Typography variant="h3" color="secondary" gutterBottom>
                {documentsProcessed}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Last 30 days
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <WarningIcon color="error" sx={{ mr: 1 }} />
                <Typography variant="h6">Active Alerts</Typography>
              </Box>
              <Typography variant="h3" color="error" gutterBottom>
                {alertsCount}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Require attention
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <TrendingUpIcon color="success" sx={{ mr: 1 }} />
                <Typography variant="h6">Gaps Identified</Typography>
              </Box>
              <Typography variant="h3" color="success" gutterBottom>
                {gapsIdentified}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                In compliance data
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Main Content */}
      <Grid container spacing={3}>
        {/* Compliance Metrics */}
        <Grid item xs={12} lg={8}>
          <Paper sx={{ p: 3, height: 'fit-content' }}>
            <Typography variant="h5" gutterBottom>
              CSRD Compliance Metrics
            </Typography>
            <ComplianceMetrics />
          </Paper>
        </Grid>

        {/* Alerts Panel */}
        <Grid item xs={12} lg={4}>
          <Paper sx={{ p: 3, height: 'fit-content' }}>
            <Typography variant="h5" gutterBottom>
              Recent Alerts
            </Typography>
            <AlertsPanel />
          </Paper>
        </Grid>

        {/* Data Upload */}
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h5" gutterBottom>
              Upload ESG Documents
            </Typography>
            <DataUpload />
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard; 