import React from 'react';
import { Link } from 'react-router-dom';
import styled from 'styled-components';

const NotFoundContainer = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 70vh;
  text-align: center;
`;

const NotFoundTitle = styled.h1`
  font-size: 6rem;
  margin: 0;
  color: #0f3460;
`;

const NotFoundText = styled.p`
  font-size: 1.5rem;
  margin: 20px 0;
  color: #666;
`;

const HomeLink = styled(Link)`
  display: inline-block;
  background-color: #0f3460;
  color: white;
  padding: 12px 24px;
  border-radius: 4px;
  font-weight: 500;
  margin-top: 20px;
  transition: background-color 0.3s;
  
  &:hover {
    background-color: #16213e;
    text-decoration: none;
  }
`;

const NotFound: React.FC = () => {
  return (
    <NotFoundContainer>
      <NotFoundTitle>404</NotFoundTitle>
      <NotFoundText>Oops! The page you're looking for doesn't exist.</NotFoundText>
      <HomeLink to="/">Go to Dashboard</HomeLink>
    </NotFoundContainer>
  );
};

export default NotFound;