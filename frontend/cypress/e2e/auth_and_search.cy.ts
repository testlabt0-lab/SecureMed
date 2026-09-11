describe('Authentication and Core Flows', () => {
  beforeEach(() => {
    // Visit the login page
    cy.visit('/login');
  });

  it('successfully logs in with valid credentials', () => {
    // Assuming there are input fields with type 'email' and 'password'
    cy.get('input[type="email"]').type('doctor@securemed.com');
    cy.get('input[type="password"]').type('SecurePass123!');
    
    // Assuming there's a submit button
    cy.get('button[type="submit"]').click();
    
    // Wait for redirect to dashboard
    cy.url().should('include', '/dashboard');
    
    // Verify dashboard elements
    cy.contains('مرحباً').should('be.visible');
  });

  it('can open global search with Ctrl+K', () => {
    // Mock a successful login state (e.g. set token in localStorage)
    cy.window().then((win) => {
      win.localStorage.setItem('auth-storage', JSON.stringify({ state: { token: 'mock-token', user: { role: 'DOCTOR' } } }));
    });
    cy.visit('/dashboard');
    
    // Trigger Ctrl+K
    cy.get('body').type('{ctrl}k');
    
    // Search modal should be visible
    cy.get('input[placeholder="ابحث عن مريض، موعد، تقرير..."]').should('be.visible');
    
    // Type something
    cy.get('input[placeholder="ابحث عن مريض، موعد، تقرير..."]').type('أحمد');
    
    // Wait for results
    cy.contains('نتائج').should('exist');
  });
});
