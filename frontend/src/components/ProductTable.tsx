import React from 'react';
import styled from 'styled-components';

const Table = styled.table`
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  border-radius: 8px;
  overflow: hidden;
`;

const TableHead = styled.thead`
  background-color: #0f3460;
  color: white;
`;

const TableRow = styled.tr`
  &:nth-child(even) {
    background-color: #f9f9f9;
  }
  
  &:hover {
    background-color: #f0f0f0;
  }
`;

const TableHeader = styled.th`
  padding: 12px 16px;
  text-align: left;
  font-weight: 600;
  font-size: 14px;
`;

const TableCell = styled.td`
  padding: 12px 16px;
  border-top: 1px solid #eee;
  font-size: 14px;
  vertical-align: middle;
`;

const ProductImage = styled.img`
  width: 50px;
  height: 50px;
  object-fit: cover;
  border-radius: 4px;
  cursor: pointer;
  transition: transform 0.2s;
  
  &:hover {
    transform: scale(1.1);
  }
`;

const NoImagePlaceholder = styled.div`
  width: 50px;
  height: 50px;
  background-color: #eee;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  color: #999;
  font-size: 10px;
`;

const ActionButton = styled.button`
  background-color: #0f3460;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 6px 12px;
  font-size: 14px;
  cursor: pointer;
  transition: background-color 0.2s;
  
  &:hover {
    background-color: #16213e;
  }
  
  &:focus {
    outline: none;
    box-shadow: 0 0 0 2px rgba(15, 52, 96, 0.2);
  }
`;

const StatusBadge = styled.span<{ $status: string }>`
  display: inline-block;
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  background-color: ${props => {
    switch (props.$status) {
      case 'active':
        return '#e1f5e1';
      case 'inactive':
        return '#f5e1e1';
      case 'pending':
        return '#f5f5e1';
      case 'draft':
        return '#e1e1f5';
      default:
        return '#f0f0f0';
    }
  }};
  color: ${props => {
    switch (props.$status) {
      case 'active':
        return '#2e7d32';
      case 'inactive':
        return '#c62828';
      case 'pending':
        return '#f9a825';
      case 'draft':
        return '#1565c0';
      default:
        return '#757575';
    }
  }};
`;

const PlatformBadge = styled.span`
  display: inline-block;
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  background-color: #e1e1f5;
  color: #1565c0;
  margin-right: 4px;
  margin-bottom: 4px;
`;

const PlatformContainer = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
`;

interface Product {
  sku: string;
  data: {
    title?: string;
    price?: number;
    quantity?: number;
    status?: string;
    image_url?: string;
    [key: string]: any;
  };
  platforms?: string[];
}

interface ProductTableProps {
  products: Product[];
  onEditClick: (product: Product) => void;
  onImageClick: (imageUrl: string) => void;
  showPlatforms?: boolean;
}

const ProductTable: React.FC<ProductTableProps> = ({ 
  products, 
  onEditClick, 
  onImageClick,
  showPlatforms = false
}) => {
  // Helper function to get image URL
  const getImageUrl = (product: Product): string | null => {
    if (product.data.image_url) {
      return product.data.image_url;
    }
    
    // Try common field names
    return product.data.image || 
           product.data.imageUrl || 
           product.data.img_url || 
           (Array.isArray(product.data.images) && product.data.images.length > 0 ? 
            (typeof product.data.images[0] === 'string' ? product.data.images[0] : product.data.images[0]?.url) : null) || 
           null;
  };
  
  // Check if the image URL is a relative path and convert to absolute URL if needed
  const getAbsoluteImageUrl = (url: string | null): string | null => {
    if (!url) return null;
    
    // If the URL is already absolute, return it
    if (url.startsWith('http://') || url.startsWith('https://')) {
      return url;
    }
    
    // Otherwise, assume it's relative to the API server
    const apiBaseUrl = 'http://localhost:8000'; // Adjust this based on your API server URL
    return `${apiBaseUrl}${url.startsWith('/') ? '' : '/'}${url}`;
  };
  
  return (
    <Table>
      <TableHead>
        <TableRow>
          <TableHeader>Image</TableHeader>
          <TableHeader>SKU</TableHeader>
          <TableHeader>Title</TableHeader>
          <TableHeader>Price</TableHeader>
          <TableHeader>Quantity</TableHeader>
          <TableHeader>Status</TableHeader>
          {showPlatforms && <TableHeader>Platforms</TableHeader>}
          <TableHeader>Actions</TableHeader>
        </TableRow>
      </TableHead>
      <tbody>
        {products.map(product => {
          const imageUrl = getImageUrl(product);
          const absoluteImageUrl = getAbsoluteImageUrl(imageUrl);
          
          return (
            <TableRow key={product.sku}>
              <TableCell>
                {absoluteImageUrl ? (
                  <ProductImage 
                    src={absoluteImageUrl} 
                    alt={product.data.title || product.sku}
                    onClick={() => onImageClick(absoluteImageUrl)}
                  />
                ) : (
                  <NoImagePlaceholder>No Image</NoImagePlaceholder>
                )}
              </TableCell>
              <TableCell>{product.sku}</TableCell>
              <TableCell>{product.data.title || 'No Title'}</TableCell>
              <TableCell>
                {product.data.price !== undefined ? 
                  `$${product.data.price.toFixed(2)}` : 
                  'N/A'}
              </TableCell>
              <TableCell>{product.data.quantity !== undefined ? product.data.quantity : 'N/A'}</TableCell>
              <TableCell>
                {product.data.status ? (
                  <StatusBadge $status={product.data.status}>
                    {product.data.status.charAt(0).toUpperCase() + product.data.status.slice(1)}
                  </StatusBadge>
                ) : (
                  'N/A'
                )}
              </TableCell>
              {showPlatforms && (
                <TableCell>
                  <PlatformContainer>
                    {product.platforms && product.platforms.map(platform => (
                      <PlatformBadge key={platform}>{platform}</PlatformBadge>
                    ))}
                  </PlatformContainer>
                </TableCell>
              )}
              <TableCell>
                <ActionButton onClick={() => onEditClick(product)}>
                  Edit
                </ActionButton>
              </TableCell>
            </TableRow>
          );
        })}
      </tbody>
    </Table>
  );
};

export default ProductTable;