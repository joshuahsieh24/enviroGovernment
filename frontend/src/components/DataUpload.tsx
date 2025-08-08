import React, { useState } from 'react';
import {
  Box,
  Typography,
  Button,
  Paper,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Chip,
  Alert,
} from '@mui/material';
import {
  CloudUpload as CloudUploadIcon,
  Description as DescriptionIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
} from '@mui/icons-material';

const DataUpload: React.FC = () => {
  const [uploadedFiles, setUploadedFiles] = useState([
    {
      id: 1,
      name: 'Sustainability_Report_2024.pdf',
      status: 'processed',
      type: 'Sustainability Report',
      size: '2.4 MB',
    },
    {
      id: 2,
      name: 'ESG_Metrics_Q3.pdf',
      status: 'processing',
      type: 'ESG Metrics',
      size: '1.8 MB',
    },
    {
      id: 3,
      name: 'Carbon_Footprint_Data.xlsx',
      status: 'error',
      type: 'Carbon Data',
      size: '856 KB',
    },
  ]);

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files) {
      // Handle file upload logic here
      console.log('Files uploaded:', files);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'processed':
        return <CheckCircleIcon color="success" />;
      case 'processing':
        return <DescriptionIcon color="primary" />;
      case 'error':
        return <ErrorIcon color="error" />;
      default:
        return <DescriptionIcon />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'processed':
        return 'success';
      case 'processing':
        return 'primary';
      case 'error':
        return 'error';
      default:
        return 'default';
    }
  };

  return (
    <Box>
      {/* Upload Area */}
      <Paper
        variant="outlined"
        sx={{
          p: 4,
          textAlign: 'center',
          border: '2px dashed',
          borderColor: 'primary.main',
          backgroundColor: 'background.default',
          mb: 3,
        }}
      >
        <CloudUploadIcon sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
        <Typography variant="h6" gutterBottom>
          Upload ESG Documents
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Drag and drop files here, or click to select files
        </Typography>
        <Button
          variant="contained"
          component="label"
          startIcon={<CloudUploadIcon />}
        >
          Choose Files
          <input
            type="file"
            hidden
            multiple
            accept=".pdf,.doc,.docx,.xlsx,.csv"
            onChange={handleFileUpload}
          />
        </Button>
        <Typography variant="caption" display="block" sx={{ mt: 1 }}>
          Supported formats: PDF, DOC, DOCX, XLSX, CSV
        </Typography>
      </Paper>

      {/* File List */}
      <Box>
        <Typography variant="h6" gutterBottom>
          Recent Uploads
        </Typography>
        <List>
          {uploadedFiles.map((file) => (
            <ListItem key={file.id}>
              <ListItemIcon>
                {getStatusIcon(file.status)}
              </ListItemIcon>
              <ListItemText
                primary={file.name}
                secondary={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography variant="body2" color="text.secondary">
                      {file.type} • {file.size}
                    </Typography>
                    <Chip
                      label={file.status}
                      size="small"
                      color={getStatusColor(file.status) as any}
                    />
                  </Box>
                }
              />
            </ListItem>
          ))}
        </List>
      </Box>

      {/* Processing Status */}
      <Alert severity="info" sx={{ mt: 2 }}>
        Documents are automatically processed for CSRD compliance metrics extraction.
        Processing typically takes 2-5 minutes.
      </Alert>
    </Box>
  );
};

export default DataUpload; 