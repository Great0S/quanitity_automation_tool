import React, { useState, useEffect } from 'react';
import styled from 'styled-components';

const ModalOverlay = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
`;

const ModalContent = styled.div`
  background-color: white;
  border-radius: 8px;
  padding: 24px;
  width: 600px;
  max-width: 90%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
`;

const ModalHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid #eee;
`;

const ModalTitle = styled.h2`
  margin: 0;
  color: #0f3460;
  font-weight: 600;
`;

const CloseButton = styled.button`
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #666;
  
  &:hover {
    color: #333;
  }
`;

const Form = styled.form`
  display: flex;
  flex-direction: column;
`;

const FormGroup = styled.div`
  margin-bottom: 20px;
`;

const Label = styled.label`
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
  color: #333;
`;

const Input = styled.input`
  width: 100%;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 16px;
  transition: border-color 0.2s, box-shadow 0.2s;
  
  &:focus {
    outline: none;
    border-color: #0f3460;
    box-shadow: 0 0 0 2px rgba(15, 52, 96, 0.1);
  }
  
  &:disabled {
    background-color: #f5f5f5;
    cursor: not-allowed;
  }
`;

const TextArea = styled.textarea`
  width: 100%;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 16px;
  transition: border-color 0.2s, box-shadow 0.2s;
  resize: vertical;
  min-height: 100px;
  
  &:focus {
    outline: none;
    border-color: #0f3460;
    box-shadow: 0 0 0 2px rgba(15, 52, 96, 0.1);
  }
`;

const Select = styled.select`
  width: 100%;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 16px;
  background-color: white;
  cursor: pointer;
  transition: border-color 0.2s, box-shadow 0.2s;
  
  &:focus {
    outline: none;
    border-color: #0f3460;
    box-shadow: 0 0 0 2px rgba(15, 52, 96, 0.1);
  }
`;

const ButtonGroup = styled.div`
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
`;

const Button = styled.button`
  padding: 12px 20px;
  border-radius: 6px;
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
`;

const CancelButton = styled(Button)`
  background-color: #f5f5f5;
  border: 1px solid #ddd;
  color: #333;
  
  &:hover {
    background-color: #e5e5e5;
  }
  
  &:focus {
    outline: none;
    box-shadow: 0 0 0 2px rgba(0, 0, 0, 0.1);
  }
`;

const SaveButton = styled(Button)`
  background-color: #0f3460;
  color: white;
  border: none;
  
  &:hover {
    background-color: #16213e;
  }
  
  &:focus {
    outline: none;
    box-shadow: 0 0 0 2px rgba(15, 52, 96, 0.2);
  }
`;

const ProductImage = styled.img`
  width: 80px;
  height: 80px;
  object-fit: cover;
  border-radius: 4px;
  margin-bottom: 16px;
`;

const NoImagePlaceholder = styled.div`
  width: 80px;
  height: 80px;
  background-color: #eee;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  color: #999;
  font-size: 12px;
  margin-bottom: 16px;
`;

const TabContainer = styled.div`
  margin-bottom: 20px;
`;

const TabButtons = styled.div`
  display: flex;
  border-bottom: 1px solid #ddd;
  margin-bottom: 20px;
`;

interface TabButtonProps {
  $active: boolean;
}

const TabButton = styled.button<TabButtonProps>`
  padding: 10px 16px;
  background: ${props => props.$active ? '#0f3460' : 'transparent'};
  color: ${props => props.$active ? 'white' : '#333'};
  border: none;
  border-bottom: 2px solid ${props => props.$active ? '#0f3460' : 'transparent'};
  cursor: pointer;
  font-weight: ${props => props.$active ? '600' : '400'};
  transition: all 0.2s;
  
  &:hover {
    background-color: ${props => props.$active ? '#0f3460' : '#f5f5f5'};
  }
`;

const TabContent = styled.div`
  padding: 10px 0;
`;

const PlatformContainer = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 20px;
`;

interface PlatformBadgeProps {
  $active: boolean;
}

const PlatformBadge = styled.div<PlatformBadgeProps>`
  display: inline-block;
  padding: 6px 12px;
  border-radius: 16px;
  font-size: 14px;
  font-weight: 500;
  background-color: ${props => props.$active ? '#0f3460' : '#f0f0f0'};
  color: ${props => props.$active ? 'white' : '#333'};
  cursor: pointer;
  transition: all 0.2s;
  
  &:hover {
    background-color: ${props => props.$active ? '#16213e' : '#e0e0e0'};
  }
`;

// Helper function to get image URL based on platform
const getImageUrl = (product: Product): string | null => {
  // Different platforms store image URLs in different fields
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

interface Product {
  sku: string;
  data: {
    title?: string;
    price?: number;
    quantity?: number;
    status?: string;
    image_url?: string;
    description?: string;
    categories?: string[];
    attributes?: Record<string, any>;
    [key: string]: any;
  };
  platforms?: string[];
}

interface ProductUpdateData {
  sku: string;
  data?: Record<string, any>;
  platforms?: string[];
}

interface ProductEditModalProps {
  product: Product;
  onClose: () => void;
  onSave: (updatedProduct: ProductUpdateData) => void;
  platforms: string[];
}

// List of fields that should not be editable
const nonEditableFields = [
  'sku', 
  'image_url', 
  'images', 
  'image', 
  'platform_id', 
  'last_updated', 
  'created_at', 
  'updated_at',
  'id',
  'base_attributes',
  'product_attributes'
];

// Fields that should be rendered as textareas
const textareaFields = [
  'description',
  'long_description',
  'short_description',
  'meta_description'
];

// Fields that should be rendered as select inputs
const selectFields = {
  'status': ['active', 'inactive', 'draft', 'pending']
};

// Platform-specific field groupings
const fieldGroups = {
  'basic': ['title', 'price', 'list_price', 'quantity', 'status', 'description'],
  'details': ['barcode', 'brand', 'brand_id', 'category_id', 'category_name', 'product_main_id', 'vat_rate'],
  'shipping': ['preparing_day', 'shipment_template', 'max_purchase_quantity'],
  'advanced': [] // Will be populated with remaining fields
};

const ProductEditModal: React.FC<ProductEditModalProps> = ({ 
  product, 
  onClose, 
  onSave, 
  platforms 
}) => {
  // Initialize form data with all editable fields from product
  const [formData, setFormData] = useState<Record<string, any>>({});
  const [activeTab, setActiveTab] = useState<string>('basic');
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>(platforms);
  
  // Add all editable fields from product.data
  useEffect(() => {
    const editableFields: Record<string, any> = {};
    
    Object.entries(product.data).forEach(([key, value]) => {
      // Skip non-editable fields
      if (!nonEditableFields.includes(key)) {
        editableFields[key] = value;
      }
    });
    
    setFormData(editableFields);
  }, [product]);
  
  // Populate the advanced tab with fields not in other tabs
  useEffect(() => {
    const allFields = Object.keys(formData);
    const assignedFields = [...fieldGroups.basic, ...fieldGroups.details, ...fieldGroups.shipping];
    
    fieldGroups.advanced = allFields.filter(field => 
      !assignedFields.includes(field) && !nonEditableFields.includes(field)
    );
  }, [formData]);
  
  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value, type } = e.target as HTMLInputElement;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'number' ? parseFloat(value) : value
    }));
  };
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    // Prepare the update data in the format expected by the API
    const updateData: ProductUpdateData = {
      sku: product.sku,
      data: formData,
      platforms: selectedPlatforms
    };
    
    onSave(updateData);
  };
  
  const togglePlatform = (platform: string) => {
    setSelectedPlatforms(prev => {
      if (prev.includes(platform)) {
        return prev.filter(p => p !== platform);
      } else {
        return [...prev, platform];
      }
    });
  };
  
  // Render fields for the current tab
  const renderTabFields = (tabName: string) => {
    const fields = [];
    const fieldsToRender = fieldGroups[tabName as keyof typeof fieldGroups] || [];
    let fieldIndex = 0;
    
    // Add fields from formData that belong to this tab
    for (const key of fieldsToRender) {
      if (key in formData) {
        const value = formData[key];
        
        // Format field label
        const fieldLabel = key
          .replace(/_/g, ' ')
          .split(' ')
          .map(word => word.charAt(0).toUpperCase() + word.slice(1))
          .join(' ');
        
        // Determine field type
        if (textareaFields.includes(key)) {
          // Render as textarea
          fields.push(
            <FormGroup key={`field-${key}-${tabName}-${fieldIndex++}`}>
              <Label htmlFor={key}>{fieldLabel}</Label>
              <TextArea
                id={key}
                name={key}
                value={value || ''}
                onChange={handleChange}
                rows={4}
              />
            </FormGroup>
          );
        } else if (key in selectFields) {
          // Render as select
          fields.push(
            <FormGroup key={`field-${key}-${tabName}-${fieldIndex++}`}>
              <Label htmlFor={key}>{fieldLabel}</Label>
              <Select
                id={key}
                name={key}
                value={value || ''}
                onChange={handleChange}
              >
                {selectFields[key as keyof typeof selectFields].map((option, optIndex) => (
                  <option key={`${option}-${optIndex}`} value={option}>
                    {option.charAt(0).toUpperCase() + option.slice(1)}
                  </option>
                ))}
              </Select>
            </FormGroup>
          );
        } else {
          // Determine input type
          let fieldType = 'text';
          if (typeof value === 'number') {
            fieldType = 'number';
          } else if (key.includes('date') || key.includes('time')) {
            fieldType = 'datetime-local';
          } else if (key.includes('email')) {
            fieldType = 'email';
          } else if (key.includes('url')) {
            fieldType = 'url';
          }
          
          // Default field rendering
          fields.push(
            <FormGroup key={`field-${key}-${tabName}-${fieldIndex++}`}>
              <Label htmlFor={key}>{fieldLabel}</Label>
              <Input
                id={key}
                type={fieldType}
                name={key}
                value={value || ''}
                onChange={handleChange}
                step={fieldType === 'number' && key === 'price' ? '0.01' : fieldType === 'number' ? '1' : undefined}
                min={fieldType === 'number' ? '0' : undefined}
              />
            </FormGroup>
          );
        }
      }
    }
    
    // If this is the advanced tab, render all remaining fields
    if (tabName === 'advanced') {
      Object.entries(formData).forEach(([key, value], advancedIndex) => {
        // Skip fields that are in other tabs or non-editable
        if ([...fieldGroups.basic, ...fieldGroups.details, ...fieldGroups.shipping].includes(key) || 
            nonEditableFields.includes(key)) {
          return;
        }
        
        // Format field label
        const fieldLabel = key
          .replace(/_/g, ' ')
          .split(' ')
          .map(word => word.charAt(0).toUpperCase() + word.slice(1))
          .join(' ');
        
        // Determine field type
        if (textareaFields.includes(key)) {
          // Render as textarea
          fields.push(
            <FormGroup key={`field-${key}-advanced-${advancedIndex}`}>
              <Label htmlFor={key}>{fieldLabel}</Label>
              <TextArea
                id={key}
                name={key}
                value={value || ''}
                onChange={handleChange}
                rows={4}
              />
            </FormGroup>
          );
        } else if (key in selectFields) {
          // Render as select
          fields.push(
            <FormGroup key={`field-${key}-advanced-${advancedIndex}`}>
              <Label htmlFor={key}>{fieldLabel}</Label>
              <Select
                id={key}
                name={key}
                value={value || ''}
                onChange={handleChange}
              >
                {selectFields[key as keyof typeof selectFields].map((option, optIndex) => (
                  <option key={`${option}-${optIndex}`} value={option}>
                    {option.charAt(0).toUpperCase() + option.slice(1)}
                  </option>
                ))}
              </Select>
            </FormGroup>
          );
        } else {
          // Determine input type
          let fieldType = 'text';
          if (typeof value === 'number') {
            fieldType = 'number';
          } else if (key.includes('date') || key.includes('time')) {
            fieldType = 'datetime-local';
          } else if (key.includes('email')) {
            fieldType = 'email';
          } else if (key.includes('url')) {
            fieldType = 'url';
          }
          
          // Default field rendering
          fields.push(
            <FormGroup key={`field-${key}-advanced-${advancedIndex}`}>
              <Label htmlFor={key}>{fieldLabel}</Label>
              <Input
                id={key}
                type={fieldType}
                name={key}
                value={value || ''}
                onChange={handleChange}
                step={fieldType === 'number' && key === 'price' ? '0.01' : fieldType === 'number' ? '1' : undefined}
                min={fieldType === 'number' ? '0' : undefined}
              />
            </FormGroup>
          );
        }
      });
    }
    
    return fields;
  };
  
  const imageUrl = getImageUrl(product);
  
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
  
  const absoluteImageUrl = getAbsoluteImageUrl(imageUrl);
  
  return (
    <ModalOverlay onClick={onClose}>
      <ModalContent onClick={(e) => e.stopPropagation()}>
        <ModalHeader>
          <ModalTitle>Edit Product</ModalTitle>
          <CloseButton onClick={onClose}>&times;</CloseButton>
        </ModalHeader>
        
        {absoluteImageUrl ? (
          <ProductImage src={absoluteImageUrl} alt={product.data.title || product.sku} />
        ) : (
          <NoImagePlaceholder>No Image</NoImagePlaceholder>
        )}
        
        <Form onSubmit={handleSubmit}>
          <FormGroup>
            <Label htmlFor="sku">SKU</Label>
            <Input 
              id="sku" 
              type="text" 
              name="sku" 
              value={product.sku} 
              disabled 
            />
          </FormGroup>
          
          <FormGroup>
            <Label>Update on Platforms</Label>
            <PlatformContainer>
              {platforms.map(platform => (
                <PlatformBadge 
                  key={platform} 
                  $active={selectedPlatforms.includes(platform)}
                  onClick={() => togglePlatform(platform)}
                >
                  {platform}
                </PlatformBadge>
              ))}
            </PlatformContainer>
          </FormGroup>
          
          <TabContainer>
            <TabButtons>
              <TabButton 
                type="button"
                $active={activeTab === 'basic'} 
                onClick={() => setActiveTab('basic')}
              >
                Basic Info
              </TabButton>
              <TabButton 
                type="button"
                $active={activeTab === 'details'} 
                onClick={() => setActiveTab('details')}
              >
                Details
              </TabButton>
              <TabButton 
                type="button"
                $active={activeTab === 'shipping'} 
                onClick={() => setActiveTab('shipping')}
              >
                Shipping
              </TabButton>
              <TabButton 
                type="button"
                $active={activeTab === 'advanced'} 
                onClick={() => setActiveTab('advanced')}
              >
                Advanced
              </TabButton>
            </TabButtons>
            
            <TabContent>
              {renderTabFields(activeTab)}
            </TabContent>
          </TabContainer>
          
          <ButtonGroup>
            <CancelButton type="button" onClick={onClose}>
              Cancel
            </CancelButton>
            <SaveButton type="submit" disabled={selectedPlatforms.length === 0}>
              Save Changes
            </SaveButton>
          </ButtonGroup>
        </Form>
      </ModalContent>
    </ModalOverlay>
  );
};

export default ProductEditModal;