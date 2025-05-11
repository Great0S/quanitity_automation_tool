import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import styled from 'styled-components';
import { useAuth } from '../context/AuthContext';

const LayoutContainer = styled.div`
  display: flex;
  min-height: 100vh;
`;

const Sidebar = styled.div<{ $collapsed: boolean }>`
  width: ${props => props.$collapsed ? '60px' : '250px'};
  background-color: #0f3460;
  color: white;
  transition: width 0.3s;
  overflow: hidden;
`;

const SidebarHeader = styled.div`
  padding: 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
`;

const Logo = styled.div<{ $collapsed: boolean }>`
  font-size: 1.2rem;
  font-weight: bold;
  white-space: nowrap;
  overflow: hidden;
  opacity: ${props => props.$collapsed ? 0 : 1};
  transition: opacity 0.3s;
`;

const ToggleButton = styled.button`
  background: none;
  border: none;
  color: white;
  cursor: pointer;
  font-size: 1.2rem;
`;

const Navigation = styled.nav`
  padding: 20px 0;
`;

const NavItem = styled(Link)<{ $active: boolean }>`
  display: flex;
  align-items: center;
  padding: 10px 20px;
  color: white;
  text-decoration: none;
  transition: background-color 0.3s;
  background-color: ${props => props.$active ? 'rgba(255, 255, 255, 0.1)' : 'transparent'};
  
  &:hover {
    background-color: rgba(255, 255, 255, 0.1);
  }
`;

const NavIcon = styled.span`
  margin-right: 15px;
  width: 20px;
  text-align: center;
`;

const NavText = styled.span<{ $collapsed: boolean }>`
  white-space: nowrap;
  opacity: ${props => props.$collapsed ? 0 : 1};
  transition: opacity 0.3s;
`;

const Content = styled.main`
  flex: 1;
  padding: 20px;
  background-color: #f5f5f5;
  overflow-y: auto;
`;

const Header = styled.header`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 1px solid #eee;
`;

const UserInfo = styled.div`
  display: flex;
  align-items: center;
`;

const UserName = styled.span`
  margin-right: 10px;
`;

const LogoutButton = styled.button`
  background: none;
  border: none;
  color: #0f3460;
  cursor: pointer;
  
  &:hover {
    text-decoration: underline;
  }
`;

const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [collapsed, setCollapsed] = useState(false);
  const { logout, user } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  
  const handleLogout = () => {
    logout();
    navigate('/login');
  };
  
  const isActive = (path: string) => {
    return location.pathname === path || location.pathname.startsWith(`${path}/`);
  };
  
  return (
    <LayoutContainer>
      <Sidebar $collapsed={collapsed}>
        <SidebarHeader>
          <Logo $collapsed={collapsed}>Quantity Tool</Logo>
          <ToggleButton onClick={() => setCollapsed(!collapsed)}>
            {collapsed ? '→' : '←'}
          </ToggleButton>
        </SidebarHeader>
        
        <Navigation>
          <NavItem to="/" $active={isActive('/')}>
            <NavIcon>📊</NavIcon>
            <NavText $collapsed={collapsed}>Dashboard</NavText>
          </NavItem>
          
          <NavItem to="/products/Hepsiburada" $active={isActive('/products')}>
            <NavIcon>📦</NavIcon>
            <NavText $collapsed={collapsed}>Products</NavText>
          </NavItem>
          
          <NavItem to="/sync" $active={isActive('/sync')}>
            <NavIcon>🔄</NavIcon>
            <NavText $collapsed={collapsed}>Sync</NavText>
          </NavItem>
          
          <NavItem to="/sync/history" $active={isActive('/sync/history')}>
            <NavIcon>📜</NavIcon>
            <NavText $collapsed={collapsed}>Sync History</NavText>
          </NavItem>
          
          <NavItem to="/settings" $active={isActive('/settings')}>
            <NavIcon>⚙️</NavIcon>
            <NavText $collapsed={collapsed}>Settings</NavText>
          </NavItem>
        </Navigation>
      </Sidebar>
      
      <Content>
        <Header>
          <UserInfo>
            <UserName>Welcome, {user?.username || 'User'}</UserName>
            <LogoutButton onClick={handleLogout}>Logout</LogoutButton>
          </UserInfo>
        </Header>
        
        {children}
      </Content>
    </LayoutContainer>
  );
};

export default Layout;