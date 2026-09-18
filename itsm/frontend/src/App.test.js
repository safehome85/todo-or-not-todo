import { render, screen } from '@testing-library/react';
import App from './App';

test('renders login header', () => {
  render(<App />);
  const headerElement = screen.getAllByText(/Login/i)[0];
  expect(headerElement).toBeInTheDocument();
});
