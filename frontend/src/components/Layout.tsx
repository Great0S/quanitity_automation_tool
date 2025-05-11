import React from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import styled from 'styled-components';

const LayoutContainer = styled.div`
  display: flex;
  min-height: 100vh;
`;

const Sidebar = styled.aside`
  width: 250px;
  background-color: #1a1a2e;
  color: #fff;
  padding: 20px 0;
`;

const MainContent = styled.main`
  flex: 1;
  padding: 20px;
  background-color: #f5f5f5;
  overflow-y: auto;
`;

const Logo = styled.div`
  font-size: 1.5rem;
  font-weight: bold;
  padding: 0 20px 20px;
  border-bottom: 1px solid #333;
  margin-bottom: 20px;
`;

const NavMenu = styled.nav`
  ul {
    list-style: none;
    padding: 0;
    margin: 0;
  }
  
  li {
    margin-bottom: 5px;
  }
`;

const NavItem = styled(NavLink)`
  display: block;
  padding: 10px 20px;
  color: #ddd;
  text-decoration: none;
  transition: all 0.3s;
  
  &:hover {
    background-color: #16213e;
    color: #fff;
  }
  
  &.active {
    background-color: #0f3460;
    color: #fff;
    border-left: 4px solid #e94560;
  }
`;

const Header = styled.header`
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 0 20px;
  border-bottom: 1px solid #ddd;
  margin-bottom: 20px;
`;

const PageTitle = styled.h1`
  margin: 0;
  font-size: 1.8rem;
  color: #333;
`;

const UserMenu = styled.div`
  display: flex;
  align-items: center;
`;

const UserInfo = styled.div`
  margin-right: 15px;
  text-align: right;
`;

const Username = styled.div`
  font-weight: bold;
`;

const LogoutButton = styled.button`
  background-color: #e94560;
  color: white;
  border: none;
  padding: 8px 15px;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.3s;
  
  &:hover {
    background-color: #c81d4e;
  }
`;

const Layout: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  
  const handleLogout = () => {
    logout();
    navigate('/login');
  };
  
  return (
    <LayoutContainer>
      <Sidebar>
        <Logo>Quantity Tool</Logo>
        <NavMenu>
          <ul>
            <li><NavItem to="/">Dashboard</NavItem></li>
            <li><NavItem to="/products/N11">N11 Products</NavItem></li>
            <li><NavItem to="/products/Trendyol">Trendyol Products</NavItem></li>
            <li><NavItem to="/products/Hepsiburada">Hepsiburada Products</NavItem></li>
            <li><NavItem to="/sync">Sync Products</NavItem></li>
            <li><NavItem to="/tasks">Background Tasks</NavItem></li>
            <li><NavItem to="/settings">Settings</NavItem></li>
          </ul>
        </NavMenu>
      </Sidebar>
      
      <MainContent>
        <Header>
          <PageTitle>Quantity Automation Tool</PageTitle>
          <UserMenu>
            <UserInfo>
              <Username>{user?.username || 'User'}</Username>
            </UserInfo>
            <LogoutButton onClick={handleLogout}>Logout</LogoutButton>
          </UserMenu>
        </Header>
        
        <Outlet />
      </MainContent>
    </LayoutContainer>
  );
};

export default Layout;