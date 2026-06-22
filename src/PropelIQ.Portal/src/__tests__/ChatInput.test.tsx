import { render, screen, fireEvent } from '@testing-library/react';
import { ChatInput } from '../components/ChatBot/ChatInput';

describe('ChatInput', () => {
  it('renders textarea and send button', () => {
    render(
      <ChatInput
        onSend={jest.fn()}
        disabled={false}
        onSwitchToManual={jest.fn()}
        suggestManualFallback={false}
      />
    );
    expect(screen.getByRole('textbox')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /send message/i })).toBeInTheDocument();
  });

  it('calls onSend with trimmed text when form submitted', () => {
    const onSend = jest.fn();
    render(
      <ChatInput
        onSend={onSend}
        disabled={false}
        onSwitchToManual={jest.fn()}
        suggestManualFallback={false}
      />
    );
    const textarea = screen.getByRole('textbox');
    fireEvent.change(textarea, { target: { value: '  my message  ' } });
    fireEvent.submit(textarea.closest('form')!);
    expect(onSend).toHaveBeenCalledWith('my message');
  });

  it('does not call onSend when input is empty', () => {
    const onSend = jest.fn();
    render(
      <ChatInput
        onSend={onSend}
        disabled={false}
        onSwitchToManual={jest.fn()}
        suggestManualFallback={false}
      />
    );
    fireEvent.submit(screen.getByRole('textbox').closest('form')!);
    expect(onSend).not.toHaveBeenCalled();
  });

  it('shows fallback banner when suggestManualFallback is true', () => {
    render(
      <ChatInput
        onSend={jest.fn()}
        disabled={false}
        onSwitchToManual={jest.fn()}
        suggestManualFallback={true}
      />
    );
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText(/switch to manual form/i)).toBeInTheDocument();
  });

  it('calls onSwitchToManual when fallback button clicked', () => {
    const onSwitch = jest.fn();
    render(
      <ChatInput
        onSend={jest.fn()}
        disabled={false}
        onSwitchToManual={onSwitch}
        suggestManualFallback={true}
      />
    );
    fireEvent.click(screen.getByRole('button', { name: /switch to manual form/i }));
    expect(onSwitch).toHaveBeenCalled();
  });
});
