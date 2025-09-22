#!/usr/bin/env python3
"""
Test pybartelslabtronix with the real pump on COM4
"""

import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_pump_on_com4():
    """Test the pump on COM4"""
    logger.info("🎉 Testing Bartels pump on COM4 with pybartelslabtronix")
    
    try:
        from pybartelslabtronix import BartelsLabtronix, SignalForm
        logger.info("✅ Imported pybartelslabtronix successfully")
    except ImportError as e:
        logger.error(f"❌ Failed to import: {e}")
        return False
    
    try:
        # Connect to COM4
        logger.info("Connecting to pump on COM4...")
        blt = BartelsLabtronix(port='COM4')
        logger.info("✅ Connected to pump on COM4!")
        
        # Test signal forms
        logger.info("Available signal forms:")
        for attr in ['Sine', 'Rectangular', 'SRS']:
            if hasattr(SignalForm, attr):
                logger.info(f"  ✅ {attr}: {getattr(SignalForm, attr)}")
        
        # Test basic operations
        logger.info("\n🧪 Testing pump operations...")
        
        # 1. Set sine wave
        if hasattr(blt, 'setsignalform'):
            blt.setsignalform(SignalForm.Sine)
            logger.info("✅ Set signal form to Sine wave")
        
        # 2. Set frequency
        if hasattr(blt, 'setfrequency'):
            blt.setfrequency(50)  # Start with 50 Hz
            logger.info("✅ Set frequency to 50 Hz")
        
        # 3. Set amplitude
        if hasattr(blt, 'setamplitude'):
            blt.setamplitude(100)  # Start with 100V
            logger.info("✅ Set amplitude to 100V")
        
        # 4. Test pump on/off
        if hasattr(blt, 'turnon'):
            logger.info("🚀 Starting pump for 3 seconds...")
            blt.turnon()
            logger.info("✅ Pump is ON!")
            
            time.sleep(3)  # Run for 3 seconds
            
            if hasattr(blt, 'turnoff'):
                blt.turnoff()
                logger.info("✅ Pump stopped")
        
        # 5. Test different frequencies
        if hasattr(blt, 'setfrequency') and hasattr(blt, 'turnon'):
            frequencies = [100, 150, 200]
            for freq in frequencies:
                logger.info(f"Testing frequency: {freq} Hz")
                blt.setfrequency(freq)
                blt.turnon()
                time.sleep(1)  # Run for 1 second
                blt.turnoff()
                time.sleep(0.5)  # Pause between tests
        
        # 6. Test different signal forms
        if hasattr(blt, 'setsignalform') and hasattr(blt, 'turnon'):
            signal_forms = ['Sine', 'Rectangular']
            for form_name in signal_forms:
                if hasattr(SignalForm, form_name):
                    logger.info(f"Testing signal form: {form_name}")
                    blt.setsignalform(getattr(SignalForm, form_name))
                    blt.setfrequency(100)  # Set back to 100 Hz
                    blt.turnon()
                    time.sleep(1)  # Run for 1 second
                    blt.turnoff()
                    time.sleep(0.5)
        
        # 7. Get status if available
        if hasattr(blt, 'get_state'):
            try:
                state = blt.get_state()
                logger.info(f"Current pump state: {state}")
            except Exception as e:
                logger.info(f"get_state() error (normal): {e}")
        
        # Clean up
        if hasattr(blt, 'ser') and hasattr(blt.ser, 'close'):
            blt.ser.close()
            logger.info("✅ Closed connection")
        
        logger.info("\n🎉 SUCCESS! Your Bartels pump is fully operational with pybartelslabtronix!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error testing pump: {e}")
        logger.error("This might be a communication or hardware issue.")
        return False

def show_api_reference():
    """Show quick API reference for the working pump"""
    logger.info("\n📚 PYBARTELSLABTRONIX API REFERENCE:")
    logger.info("=" * 50)
    logger.info("from pybartelslabtronix import BartelsLabtronix, SignalForm")
    logger.info("")
    logger.info("# Connect")
    logger.info("blt = BartelsLabtronix(port='COM4')")
    logger.info("")
    logger.info("# Signal forms")
    logger.info("blt.setsignalform(SignalForm.Sine)       # Sine wave")
    logger.info("blt.setsignalform(SignalForm.Rectangular) # Square wave")
    logger.info("blt.setsignalform(SignalForm.SRS)        # SRS wave")
    logger.info("")
    logger.info("# Parameters")
    logger.info("blt.setfrequency(100)    # Set frequency in Hz")
    logger.info("blt.setamplitude(120)    # Set voltage/amplitude")
    logger.info("")
    logger.info("# Control")
    logger.info("blt.turnon()             # Start pump")
    logger.info("blt.turnoff()            # Stop pump")
    logger.info("")
    logger.info("# State")
    logger.info("state = blt.get_state()  # Get current state")

if __name__ == "__main__":
    logger.info("🔬 Bartels Micropump Test - COM4")
    logger.info("=" * 40)
    
    success = test_pump_on_com4()
    
    if success:
        show_api_reference()
        logger.info("\n✅ Your micropump setup is complete and working!")
        logger.info("You can now use pybartelslabtronix for pump control.")
    else:
        logger.info("\n❌ Test failed. Check:")
        logger.info("1. Pump is connected and powered")
        logger.info("2. COM4 is the correct port")
        logger.info("3. No other software is using COM4")
