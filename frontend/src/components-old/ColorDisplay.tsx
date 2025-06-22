import { useState, useEffect } from 'react';
import { Color, ColorListResponse, listColors } from '../services/ColorService';
import './ColorDisplay.css';

export const ColorDisplay = () => {
  const [colors, setColors] = useState<Color[]>([]);
  const [metadata, setMetadata] = useState<{ totalColors: number } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchColors = async () => {
      try {
        const response = await listColors();
        setColors(response.colors || []);
        setMetadata(response.metadata);
        setLoading(false);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch colors');
        setLoading(false);
      }
    };

    fetchColors();
  }, []);

  if (loading) return (
    <div className="color-display">
      <div className="loading">
        Loading color palette...
      </div>
    </div>
  );

  if (error) return (
    <div className="color-display">
      <div className="error">
        <h3>Error Loading Colors</h3>
        <p>{error}</p>
      </div>
    </div>
  );

  return (
    <div className="color-display">
      <h2>Color Palette</h2>
      {metadata && (
        <div className="metadata">
          <p>Total Colors: {metadata.totalColors}</p>
        </div>
      )}
      <div className="color-grid">
        {colors.map((color) => (
          <div key={color.id || color.hex} className="color-item">
            <div 
              className="color-swatch" 
              style={{ backgroundColor: color.hex }}
              title={`${color.name} - ${color.hex}`}
            />
            <div className="color-info">
              <h3>{color.name}</h3>
              <p>{color.hex}</p>
              {color.rgb && <p>{color.rgb}</p>}
              {color.hsl && <p>{color.hsl}</p>}
              {color.category && (
                <p className="category">
                  {color.category}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}; 