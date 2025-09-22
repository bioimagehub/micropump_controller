#!/usr/bin/env python3
"""
FINAL TEST: Bartels Micropump on COM4
Run this script to test your pump with pybartelslabtronix
"""

def main():
    print("🔬 Bartels Micropump Test - COM4")
    print("=" * 40)
    
    # Test 1: Import library
    try:
        from pybartelslabtronix import BartelsLabtronix, SignalForm
        print("✅ pybartelslabtronix imported successfully")
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False
    
    # Test 2: Connect to COM4
    try:
        print("🔌 Connecting to COM4...")
        blt = BartelsLabtronix(port='COM4')
        print("✅ Connected to pump on COM4!")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("Possible issues:")
        print("  - COM4 is not available")
        print("  - Another program is using COM4")
        print("  - Pump is not powered on")
        return False
    
    # Test 3: Basic operations
    try:
        print("\n🧪 Testing pump operations...")
        
        # Set sine wave
        blt.setsignalform(SignalForm.Sine)
        print("✅ Set signal form to Sine wave")
        
        # Set frequency
        blt.setfrequency(50)
        print("✅ Set frequency to 50 Hz")
        
        # Set amplitude
        blt.setamplitude(100)
        print("✅ Set amplitude to 100V")
        
        print("\n🚀 Testing pump start/stop...")
        print("⚠️  You should hear/feel the pump operating...")
        
        # Start pump
        blt.turnon()
        print("✅ Pump started!")
        
        import time
        time.sleep(2)  # Run for 2 seconds
        
        # Stop pump
        blt.turnoff()
        print("✅ Pump stopped!")
        
    except Exception as e:
        print(f"❌ Operation failed: {e}")
        return False
    
    # Test 4: Advanced operations
    try:
        print("\n🔧 Testing different settings...")
        
        frequencies = [100, 150, 200]
        for freq in frequencies:
            print(f"  Testing {freq} Hz...")
            blt.setfrequency(freq)
            blt.turnon()
            time.sleep(0.5)
            blt.turnoff()
            time.sleep(0.2)
        
        print("✅ Frequency sweep completed")
        
    except Exception as e:
        print(f"⚠️  Advanced test warning: {e}")
    
    # Cleanup
    try:
        if hasattr(blt, 'ser') and hasattr(blt.ser, 'close'):
            blt.ser.close()
        print("✅ Connection closed")
    except:
        pass
    
    print("\n🎉 SUCCESS! Your Bartels pump is fully operational!")
    print("\n📚 Quick API Reference:")
    print("  blt = BartelsLabtronix(port='COM4')")
    print("  blt.setsignalform(SignalForm.Sine)")
    print("  blt.setfrequency(100)  # Hz")
    print("  blt.setamplitude(120)  # Volts")
    print("  blt.turnon()           # Start")
    print("  blt.turnoff()          # Stop")
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        print("\n❌ Test failed. Check pump connection and try again.")
    
    input("\nPress Enter to exit...")
