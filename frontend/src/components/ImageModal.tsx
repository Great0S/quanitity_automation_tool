import React from 'react';
import styled from 'styled-components';

const ModalOverlay = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  cursor: pointer;
  backdrop-filter: blur(5px);
  transition: opacity 0.3s ease;
  animation: fadeIn 0.3s ease;
  
  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }
`;

const ModalImage = styled.img`
  max-width: 90%;
  max-height: 90vh;
  object-fit: contain;
  border-radius: 4px;
  box-shadow: 0 5px 30px rgba(0, 0, 0, 0.3);
  cursor: default;
  animation: scaleIn 0.3s ease;
  
  @keyframes scaleIn {
    from { transform: scale(0.9); }
    to { transform: scale(1); }
  }
`;

const CloseButton = styled.button`
  position: absolute;
  top: 20px;
  right: 20px;
  background: rgba(0, 0, 0, 0.3);
  border: none;
  color: white;
  font-size: 32px;
  width: 50px;
  height: 50px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background-color 0.2s;
  
  &:hover {
    background: rgba(0, 0, 0, 0.5);
  }
  
  &:focus {
    outline: none;
    box-shadow: 0 0 0 3px rgba(255, 255, 255, 0.3);
  }
`;

const ImageCaption = styled.div`
  position: absolute;
  bottom: 20px;
  left: 0;
  right: 0;
  text-align: center;
  color: white;
  padding: 10px;
  font-size: 16px;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(5px);
`;

interface ImageModalProps {
  imageUrl: string;
  onClose: () => void;
  caption?: string;
}

const ImageModal: React.FC<ImageModalProps> = ({ imageUrl, onClose, caption }) => {
  // Prevent closing when clicking on the image itself
  const handleImageClick = (e: React.MouseEvent) => {
    e.stopPropagation();
  };
  
  return (
    <ModalOverlay onClick={onClose}>
      <CloseButton onClick={onClose}>&times;</CloseButton>
      <ModalImage 
        src={imageUrl} 
        alt="Enlarged product" 
        onClick={handleImageClick}
      />
      {caption && <ImageCaption>{caption}</ImageCaption>}
    </ModalOverlay>
  );
};

export default ImageModal;