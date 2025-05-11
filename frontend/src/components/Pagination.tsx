import React from 'react';
import styled from 'styled-components';

const PaginationContainer = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
`;

interface PageButtonProps {
  $active?: boolean;
}

const PageButton = styled.button<PageButtonProps>`
  min-width: 36px;
  height: 36px;
  border-radius: 4px;
  border: 1px solid ${props => props.$active ? '#0f3460' : '#ddd'};
  background-color: ${props => props.$active ? '#0f3460' : 'white'};
  color: ${props => props.$active ? 'white' : '#333'};
  font-weight: ${props => props.$active ? '600' : '400'};
  cursor: pointer;
  transition: all 0.2s;
  
  &:hover {
    background-color: ${props => props.$active ? '#0f3460' : '#f5f5f5'};
  }
  
  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    background-color: #f5f5f5;
  }
`;

const PageInfo = styled.div`
  margin: 0 10px;
  color: #666;
  font-size: 14px;
`;

interface PaginationProps {
  currentPage: number;
  totalItems: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  maxButtons?: number;
}

const Pagination: React.FC<PaginationProps> = ({
  currentPage,
  totalItems,
  pageSize,
  onPageChange,
  maxButtons = 5
}) => {
  const totalPages = Math.ceil(totalItems / pageSize);
  
  // Generate page numbers to display
  const getPageNumbers = () => {
    const pages: (number | string)[] = [];
    
    // Always show first page
    if (totalPages > 0) {
      pages.push(1);
    }
    
    // Calculate range around current page
    let rangeStart = Math.max(2, currentPage - Math.floor(maxButtons / 2));
    let rangeEnd = Math.min(totalPages - 1, rangeStart + maxButtons - 2);
    
    // Adjust range if at the edges
    if (rangeEnd - rangeStart < maxButtons - 2) {
      rangeStart = Math.max(2, rangeEnd - maxButtons + 2);
    }
    
    // Add ellipsis after first page if needed
    if (rangeStart > 2) {
      pages.push('ellipsis1');
    }
    
    // Add pages in range
    for (let i = rangeStart; i <= rangeEnd; i++) {
      pages.push(i);
    }
    
    // Add ellipsis before last page if needed
    if (rangeEnd < totalPages - 1) {
      pages.push('ellipsis2');
    }
    
    // Always show last page if there is more than one page
    if (totalPages > 1) {
      pages.push(totalPages);
    }
    
    return pages;
  };
  
  const pageNumbers = getPageNumbers();
  
  return (
    <PaginationContainer>
      <PageButton 
        onClick={() => onPageChange(currentPage - 1)}
        disabled={currentPage === 1}
      >
        &lt;
      </PageButton>
      
      {pageNumbers.map((page, index) => (
        page === 'ellipsis1' || page === 'ellipsis2' ? (
          <span key={page}>...</span>
        ) : (
          <PageButton
            key={index}
            $active={page === currentPage}
            onClick={() => onPageChange(Number(page))}
          >
            {page}
          </PageButton>
        )
      ))}
      
      <PageButton 
        onClick={() => onPageChange(currentPage + 1)}
        disabled={currentPage === totalPages}
      >
        &gt;
      </PageButton>
      
      <PageInfo>
        {totalItems > 0 ? 
          `${(currentPage - 1) * pageSize + 1}-${Math.min(currentPage * pageSize, totalItems)} of ${totalItems}` : 
          '0 items'}
      </PageInfo>
    </PaginationContainer>
  );
};

export default Pagination;