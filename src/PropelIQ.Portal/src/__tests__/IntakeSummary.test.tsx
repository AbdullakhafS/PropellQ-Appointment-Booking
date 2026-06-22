import { render, screen } from '@testing-library/react';
import { IntakeSummary } from '../components/ChatBot/IntakeSummary';
import type { ExtractedData } from '../types/chat';

const mockData: ExtractedData = {
  chiefComplaint: 'persistent cough',
  medicalHistory: ['asthma', 'hypertension'],
  medications: [{ name: 'metformin', dosage: '500mg', frequency: 'twice daily' }],
  allergies: [{ allergen: 'penicillin', reaction: 'rash', type: 'DrugAllergy' }],
  insuranceInfo: { provider: 'BlueCross', memberId: 'XYZ123', groupNumber: 'GRP99' },
};

describe('IntakeSummary', () => {
  it('renders chief complaint', () => {
    render(<IntakeSummary data={mockData} onConfirm={jest.fn()} onEdit={jest.fn()} />);
    expect(screen.getByText('persistent cough')).toBeInTheDocument();
  });

  it('renders medications with dosage', () => {
    render(<IntakeSummary data={mockData} onConfirm={jest.fn()} onEdit={jest.fn()} />);
    expect(screen.getByText(/metformin/i)).toBeInTheDocument();
    expect(screen.getByText(/500mg/i)).toBeInTheDocument();
  });

  it('renders allergies', () => {
    render(<IntakeSummary data={mockData} onConfirm={jest.fn()} onEdit={jest.fn()} />);
    expect(screen.getByText(/penicillin/i)).toBeInTheDocument();
  });

  it('renders insurance info', () => {
    render(<IntakeSummary data={mockData} onConfirm={jest.fn()} onEdit={jest.fn()} />);
    expect(screen.getByText('BlueCross')).toBeInTheDocument();
  });

  it('calls onConfirm when confirm button clicked', () => {
    const onConfirm = jest.fn();
    render(<IntakeSummary data={mockData} onConfirm={onConfirm} onEdit={jest.fn()} />);
    screen.getByRole('button', { name: /confirm/i }).click();
    expect(onConfirm).toHaveBeenCalled();
  });

  it('calls onEdit when edit button clicked', () => {
    const onEdit = jest.fn();
    render(<IntakeSummary data={mockData} onConfirm={jest.fn()} onEdit={onEdit} />);
    screen.getByRole('button', { name: /edit/i }).click();
    expect(onEdit).toHaveBeenCalled();
  });
});
