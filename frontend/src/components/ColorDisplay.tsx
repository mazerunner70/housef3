import { useState, useEffect } from 'react';
import { Color, ColorListResponse, listColors } from '../services/ColorService';
import './ColorDisplay.css';

export const ColorDisplay = () => {
  const [colors, setColors] = useState<Color[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchColors = async () => {
      try {
        const response = await listColors();
        setColors(response.items);
        setLoading(false);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch colors');
        setLoading(false);
      }
    };

    fetchColors();
  }, []);

  if (loading) return <div>Loading colors...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div className="color-display">
      <h2>Colors</h2>
      <div className="color-grid">
        {colors.map((color) => (
          <div key={color.id} className="color-item">
            <div 
              className="color-swatch" 
              style={{ backgroundColor: color.hex }}
            />
            <div className="color-info">
              <h3>{color.name}</h3>
              <p>HEX: {color.hex}</p>
              <p>RGB: {color.rgb}</p>
              <p>HSL: {color.hsl}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}; 