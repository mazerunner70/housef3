import { useState, useEffect } from 'react';
import { Color, ColorResponse, getColors } from '../services/ColorService';
import './ColorDisplay.css';

const ColorDisplay = () => {
  const [colorData, setColorData] = useState<ColorResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchColors = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await getColors();
        setColorData(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch colors');
        console.error('Error fetching colors:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchColors();
  }, []);

  if (loading) {
    return <div className="loading">Loading colors...</div>;
  }

  if (error) {
    return <div className="error">Error: {error}</div>;
  }

  if (!colorData || !colorData.colors.length) {
    return <div className="no-data">No colors available</div>;
  }

  return (
    <div className="color-display">
      <h2>Available Colors</h2>
      
      <div className="metadata">
        <p>Total Colors: {colorData.metadata.totalColors}</p>
        <p>Version: {colorData.metadata.version}</p>
        <p>Last Updated: {new Date(colorData.metadata.timestamp).toLocaleString()}</p>
      </div>
      
      <div className="color-grid">
        {colorData.colors.map((color, index) => (
          <div className="color-card" key={index}>
            <div 
              className="color-preview" 
              style={{ backgroundColor: color.hexCode }}
            />
            <div className="color-info">
              <h3>{color.name}</h3>
              <p className="color-category">{color.category}</p>
              <p className="color-hex">{color.hexCode}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ColorDisplay; 