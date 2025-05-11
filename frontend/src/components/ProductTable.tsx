import React from 'react';
import styled from 'styled-components';

const Table = styled.table`
  width: 100%;
  border-collapse: collapse;
  margin-top: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  border-radius: 8px;
  overflow: hidden;
`;

const TableHeader = styled.th`
  background-color: #f5f5f5;
  padding: 12px 16px;
  text-align: left;
  border-bottom: 2px solid #ddd;
  font-weight: 600;
  color: #333;
`;

const TableRow = styled.tr`
  &:nth-child(even) {
    background-color: #f9f9f9;
  }
  
  &:hover {
    background-color: #f1f1f1;
  }
`;

const TableCell = styled.td`
  padding: 12px 16px;
  border-bottom: 1px solid #eee;
  vertical-align: middle;
`;

const ProductImage = styled.img`
  width: 60px;
  height: 60px;
  object-fit: cover;
  border-radius: 4px;
  cursor: pointer;
  transition: transform 0.2s;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  
  &:hover {
    transform: scale(1.1);
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
  }
`;

const EditButton = styled.button`
  background-color: #0f3460;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 8px 12px;
  cursor: pointer;
  font-weight: 500;
  transition: background-color 0.2s;
  
  &:hover {
    background-color: #16213e;
  }
  
  &:focus {
    outline: none;
    box-shadow: 0 0 0 2px rgba(15, 52, 96, 0.2);
  }
`;

const NoImagePlaceholder = styled.div`
  width: 60px;
  height: 60px;
  background-color: #eee;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  color: #999;
  font-size: 10px;
  text-align: center;
`;

interface StatusBadgeProps {
  $status: string;
}

const StatusBadge = styled.span<StatusBadgeProps>`
  display: inline-block;
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  
  ${props => {
    switch (props.$status) {
      case 'active':
        return 'background-color: #e8f5e9; color: #2e7d32;';
      case 'inactive':
        return 'background-color: #ffebee; color: #c62828;';
      case 'draft':
        return 'background-color: #e3f2fd; color: #1565c0;';
      default:
        return 'background-color: #f5f5f5; color: #616161;';
    }
  }}
`;

interface Product {
  sku: string;
  data: {
    title?: string;
    price?: number;
    quantity?: number;
    status?: string;
    image_url?: string;
    images?: Array<any>;
    image?: any;
    [key: string]: any;
  };
}

interface ProductTableProps {
  products: Product[];
  onEditClick: (product: Product) => void;
  onImageClick: (imageUrl: string) => void;
  platform: string;
}

// Helper function to get image URL based on platform
const getImageUrl = (product: Product, platform: string): string | null => {
  // Different platforms store image URLs in different fields
  if (product.data.image_url) {
    return product.data.image_url;
  }
  
  // Platform-specific mappings
  switch (platform) {
    case 'Magento':
      return product.data.images?.[0]?.url || 
             product.data.image || 
             product.data.thumbnail || 
             null;
    case 'WooCommerce':
    case 'WordPress':
      return product.data.images?.[0]?.src || 
             product.data.image?.src || 
             null;
    case 'Shopify':
      return product.data.image?.src || 
             product.data.images?.[0]?.src || 
             null;
    case 'Amazon':
      return product.data.ImageUrl || 
             product.data.LargeImage?.URL || 
             null;
    case 'eBay':
      return product.data.PictureDetails?.PictureURL?.[0] || 
             product.data.pictureUrl || 
             null;
    case 'Trendyol':
      return Array.isArray(product.data.images) && product.data.images.length > 0 ? 
             (typeof product.data.images[0] === 'string' ? product.data.images[0] : product.data.images[0]?.url) || 
             product.data.image || 
             null : null;
    case 'Hepsiburada':
      return Array.isArray(product.data.images) && product.data.images.length > 0 ? 
             (typeof product.data.images[0] === 'string' ? product.data.images[0] : product.data.images[0]?.url) || 
             product.data.imageUrl || 
             null : null;
    case 'N11':
      return Array.isArray(product.data.images) && product.data.images.length > 0 ? 
             (typeof product.data.images[0] === 'string' ? product.data.images[0] : null) || 
             product.data.imageUrl || 
             null : null;
    default:
      // Try common field names
      return product.data.image || 
             product.data.imageUrl || 
             product.data.img_url || 
             (Array.isArray(product.data.images) && product.data.images.length > 0 ? 
              (typeof product.data.images[0] === 'string' ? product.data.images[0] : product.data.images[0]?.url) : null) || 
             null;
  }
};

// Helper function to format price based on platform
const formatPrice = (product: Product, platform: string): string => {
  let price: number | undefined;
  
  // Different platforms store prices in different fields
  if (product.data.price !== undefined) {
    price = product.data.price;
  } else {
    // Platform-specific mappings
    switch (platform) {
      case 'Magento':
        price = product.data.price_info?.final_price || 
                product.data.price_info?.regular_price || 
                undefined;
        break;
      case 'WooCommerce':
      case 'WordPress':
        price = product.data.regular_price || 
                product.data.price || 
                product.data.sale_price || 
                undefined;
        break;
      case 'Shopify':
        price = product.data.variants?.[0]?.price || 
                product.data.price || 
                undefined;
        break;
      case 'Amazon':
        price = product.data.Price?.Amount || 
                product.data.ListPrice?.Amount || 
                undefined;
        break;
      case 'eBay':
        price = product.data.StartPrice?.value || 
                product.data.price || 
                undefined;
        break;
      case 'Trendyol':
        price = product.data.salePrice || 
                product.data.price || 
                undefined;
        break;
      case 'Hepsiburada':
        price = product.data.price || 
                product.data.listPrice || 
                undefined;
        break;
      case 'N11':
        price = product.data.price || 
                product.data.displayPrice || 
                undefined;
        break;
      default:
        // Try common field names
        price = product.data.price || 
                product.data.salePrice || 
                product.data.listPrice || 
                undefined;
    }
  }
  
  if (price === undefined) {
    return 'N/A';
  }
  
  // Format price with currency symbol
  return `$${price.toFixed(2)}`;
};

const ProductTable: React.FC<ProductTableProps> = ({ products, onEditClick, onImageClick, platform }) => {
  return (
    <Table>
      <thead>
        <tr>
          <TableHeader>Image</TableHeader>
          <TableHeader>SKU</TableHeader>
          <TableHeader>Title</TableHeader>
          <TableHeader>Price</TableHeader>
          <TableHeader>Quantity</TableHeader>
          <TableHeader>Status</TableHeader>
          <TableHeader>Actions</TableHeader>
        </tr>
      </thead>
      <tbody>
        {products.map((product, index) => {
          const imageUrl = getImageUrl(product, platform);
          
          return (
            <TableRow key={`${product.sku}-${index}`}>
              <TableCell>
                {imageUrl ? (
                  <ProductImage 
                    src={imageUrl} 
                    alt={product.data.title || product.sku}
                    onClick={() => onImageClick(imageUrl)}
                    onError={(e) => {
                      // Handle image load error
                      (e.target as HTMLImageElement).style.display = 'none';
                      (e.target as HTMLImageElement).parentElement!.innerHTML = 'Image Error';
                    }}
                  />
                ) : (
                  <NoImagePlaceholder>No Image</NoImagePlaceholder>
                )}
              </TableCell>
              <TableCell>{product.sku}</TableCell>
              <TableCell>{product.data.title || 'No Title'}</TableCell>
              <TableCell>{formatPrice(product, platform)}</TableCell>
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
              <TableCell>
                <EditButton onClick={() => onEditClick(product)}>
                  Edit
                </EditButton>
              </TableCell>
            </TableRow>
          );
        })}
      </tbody>
    </Table>
  );
};

export default ProductTable;