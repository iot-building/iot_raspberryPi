import smbus2
import time
import RPi.GPIO as gpio

button_pin = 21

gpio.setmode(gpio.BCM)
gpio.setup(button_pin, gpio.IN, pull_up_down=gpio.PUD_UP)

# LCD 기본 설정
I2C_ADDR = 0x27  # LCD 주소 (i2cdetect로 확인)
LCD_WIDTH = 16   # 문자 수 (16x2 LCD)
LCD_CHR = 1
LCD_CMD = 0

LCD_LINE_1 = 0x80  # 1번째 줄 주소
LCD_LINE_2 = 0xC0  # 2번째 줄 주소

LCD_BACKLIGHT = 0x08  # 백라이트 ON
ENABLE = 0b00000100   # Enable 비트

# I2C 버스 객체
bus = smbus2.SMBus(1)
def lcd_byte(bits, mode):
    """명령 또는 데이터 전송"""
    bits_high = mode | (bits & 0xF0) | LCD_BACKLIGHT
    bits_low = mode | ((bits << 4) & 0xF0) | LCD_BACKLIGHT

    bus.write_byte(I2C_ADDR, bits_high)
    lcd_toggle_enable(bits_high)
    bus.write_byte(I2C_ADDR, bits_low)
    lcd_toggle_enable(bits_low)

def lcd_toggle_enable(bits):
    """Enable 펄스 주기"""
    time.sleep(0.0005)
    bus.write_byte(I2C_ADDR, (bits | ENABLE))
    time.sleep(0.0005)
    bus.write_byte(I2C_ADDR, (bits & ~ENABLE))
    time.sleep(0.0005)

def lcd_init():
    """LCD 초기화"""
    lcd_byte(0x33, LCD_CMD)  # 초기화 시퀀스
    lcd_byte(0x32, LCD_CMD)
    lcd_byte(0x06, LCD_CMD)
    lcd_byte(0x0C, LCD_CMD)  # 디스플레이 ON
    lcd_byte(0x28, LCD_CMD)  # 4비트, 2라인, 5x8 폰트
    lcd_byte(0x01, LCD_CMD)  # 화면 클리어
    time.sleep(0.005)

def lcd_string(message, line):
    """LCD에 문자열 표시"""
    message = message.ljust(LCD_WIDTH, " ")
    lcd_byte(line, LCD_CMD)
    for i in range(LCD_WIDTH):
        lcd_byte(ord(message[i]), LCD_CHR)

# 메인 루프
if __name__ == '__main__':
    try:
        while True:
            lcd_init()
            lcd_string("Warning!!", LCD_LINE_1)
            lcd_string("Fire Outbreak!", LCD_LINE_2)
            time.sleep(0.5)
            
            lcd_byte(0x01, LCD_CMD)
            time.sleep(0.05)
    except KeyboardInterrupt:
        pass
    finally:
        lcd_byte(0x01, LCD_CMD)  # LCD 클리어
        bus.close()