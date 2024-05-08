import cv2
import numpy as np
import time

def display_interlock_status(frame, side, blink_on):
    interlock_signals_right = {
        'enable': True,
        'detection': True,
        'emergency_button': True,
        'light_curtain': True,
        'emergency_cord': False
    }

    if side == 'right':
        interlock_signals = interlock_signals_right

    if not interlock_signals['enable']:
        return


    active_signals = [signal for signal, active in interlock_signals.items() if active and signal != 'enable']

    translations = {
        'detection': 'Pessoa Detectada',
        'emergency_button': 'Botao de Emergencia Pressionado',
        'light_curtain': 'Cortina de Luz Acionada',
        'emergency_cord': 'Corda de Emergencia Acionada'
    }

    text = "Intertravamento Ativado"
    color = (0, 0, 255)  # Red text
    background_color = (245, 245, 225)  # Light white background
    text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 3, 6)[0]
    text_x = 2320  # Keep original positioning for right side
    text_y = 850

    for i, signal in enumerate(active_signals):
        signal_text = translations[signal]
        signal_text_size = cv2.getTextSize(signal_text, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)[0]
        signal_y = text_y + (i + 1) * 40
        signal_color = (0, 255, 255)  # Yellow text
        signal_background_color = (127, 127, 127)  # Gray background
        # Adjust the rectangle width based on the text size
        cv2.rectangle(frame, (text_x, signal_y - 30), (text_x + signal_text_size[0] + 10, signal_y + 1), signal_background_color, -1)
        cv2.putText(frame, signal_text, (text_x + 3, signal_y - 3), cv2.FONT_HERSHEY_SIMPLEX, 1, signal_color, 2)

    # Check if it's the "off" second for blinking and return without drawing
    if not blink_on:
        return


    # Always draw the text
    cv2.rectangle(frame, (text_x, text_y - text_size[1] - 30), (text_x + text_size[0] + 20, text_y - 10), background_color, -1)
    cv2.putText(frame, text, (text_x + 10, text_y - 20), cv2.FONT_HERSHEY_SIMPLEX, 3, color, 8)


def main():
    original_frame = np.zeros((1080, 3840, 3), dtype=np.uint8)
    last_blink_time = time.time()
    blink_on = True  # Start with blinking on

    while True:
        frame = original_frame.copy()
        current_time = time.time()

        # Toggle blink_on every second
        if current_time - last_blink_time >= 2.0:
            blink_on = not blink_on
            last_blink_time = current_time

        display_interlock_status(frame, 'right', blink_on)
        resized_frame = cv2.resize(frame, (1920, 1080))  # Resize to fit the screen
        cv2.imshow('Interlock Status Test', resized_frame)
        if cv2.waitKey(100) & 0xFF == ord('q'):  # Check more frequently to quit
            break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
