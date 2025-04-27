import React from 'react';
import ReactApexChart from 'react-apexcharts';
import { FileMetadata } from '../services/FileService';
import './TimelineView.css';

interface TimelineViewProps {
  files: FileMetadata[];
  onFileClick?: (fileId: string) => void;
  onGapClick?: (startDate: number, endDate: number) => void;
}

interface TimelineDataItem {
  x: string;
  y: [number, number];
  fileId?: string;
  transactionCount?: number;
  isGap?: boolean;
}

const TimelineView: React.FC<TimelineViewProps> = ({ files, onFileClick, onGapClick }) => {
  // Sort files by start date
  const sortedFiles = [...files].sort((a, b) => a.startDate - b.startDate);

  const generateChartData = (): TimelineDataItem[] => {
    const data: TimelineDataItem[] = sortedFiles.map((file) => ({
      x: file.fileName,
      y: [file.startDate, file.endDate],
      fileId: file.fileId,
      transactionCount: file.transactionCount
    }));

    // Find gaps between files
    for (let i = 0; i < sortedFiles.length - 1; i++) {
      const currentFile = sortedFiles[i];
      const nextFile = sortedFiles[i + 1];
      const daysDiff = Math.floor((nextFile.startDate - currentFile.endDate) / (1000 * 60 * 60 * 24));

      if (daysDiff > 1) {
        data.push({
          x: `Gap (${daysDiff} days)`,
          y: [currentFile.endDate + 86400000, nextFile.startDate - 86400000], // Add/subtract one day in ms
          isGap: true
        });
      }
    }

    return data;
  };

  const chartData = generateChartData();

  // Find the earliest start date
  const earliestStart = sortedFiles.length > 0 ? sortedFiles[0].startDate : Date.now();
  // Calculate 3 months before earliest start
  const minX = new Date(earliestStart);
  minX.setMonth(minX.getMonth() - 3);
  // Current day
  const maxX = Date.now();

  const options = {
    chart: {
      height: 350,
      type: 'rangeBar' as const,
      toolbar: {
        show: false
      },
      events: {
        click: function(event: any, chartContext: any, config: any) {
          const dataPointIndex = config.dataPointIndex;
          if (dataPointIndex >= 0) {
            const item = chartData[dataPointIndex];
            if (item.isGap && onGapClick) {
              onGapClick(item.y[0], item.y[1]);
            } else if (!item.isGap && onFileClick && item.fileId) {
              onFileClick(item.fileId);
            }
          }
        }
      }
    },
    plotOptions: {
      bar: {
        horizontal: true,
        barHeight: '80%',
        rangeBarGroupRows: true
      }
    },
    dataLabels: {
      enabled: true,
      style: {
        colors: ['#333']
      },
      formatter: function(val: any, opts: any) {
        const item = chartData[opts.dataPointIndex];
        if (item.isGap) return '';
        return item.transactionCount !== undefined ? `${item.transactionCount} txns` : '';
      },
      background: {
        enabled: true,
        borderRadius: 2,
        padding: 2,
        opacity: 0.8,
        borderWidth: 0,
        dropShadow: {
          enabled: false
        }
      }
    },
    xaxis: {
      type: 'datetime' as const,
      labels: {
        format: 'MM/dd/yyyy'
      },
      min: minX.getTime(),
      max: maxX
    },
    yaxis: {
      labels: {
        style: {
          fontSize: '12px'
        }
      }
    },
    colors: ['#1976d2', '#f57c00'],
    fill: {
      type: 'solid',
      opacity: 1
    },
    legend: {
      show: false
    },
    tooltip: {
      custom: function({ seriesIndex, dataPointIndex, w }: any) {
        const item = chartData[dataPointIndex];
        const startDate = new Date(item.y[0]).toLocaleDateString();
        const endDate = new Date(item.y[1]).toLocaleDateString();
        
        if (item.isGap) {
          return `
            <div class="timeline-tooltip">
              <div class="tooltip-title">Gap Period</div>
              <div>${startDate} - ${endDate}</div>
              <div>Click to export transactions</div>
            </div>
          `;
        }
        
        return `
          <div class="timeline-tooltip">
            <div class="tooltip-title">${item.x}</div>
            <div>${startDate} - ${endDate}</div>
            <div>${item.transactionCount} transactions</div>
          </div>
        `;
      }
    }
  };

  const series = [{
    data: chartData.map(item => ({
      x: item.x,
      y: item.y,
      fillColor: item.isGap ? '#f57c00' : '#1976d2'
    }))
  }];

  if (!files.length) {
    return (
      <div className="timeline-empty">
        No files available to display timeline.
      </div>
    );
  }

  return (
    <div className="timeline-container">
      <ReactApexChart
        options={options}
        series={series}
        type="rangeBar"
        height={Math.max(120, files.length * 26 + 60)}
      />
    </div>
  );
};

export default TimelineView; 