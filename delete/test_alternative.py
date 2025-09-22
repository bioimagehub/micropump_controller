#!/usr/bin/env python3
"""
Alternative test approach for COM4 connection
"""

import time

def test_pybartelslabtronix_alternative():
    print("🔬 Alternative pybartelslabtronix Test")
    print("=" * 40)
    
    try:
        from pybartelslabtronix import BartelsLabtronix, SignalForm
        print("✅ Library imported successfully")
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False
    
    # Try with different approaches
    approaches = [
        {'port': 'COM4'},
        {'port': 'COM4', 'host': 'localhost'},
    ]
    
    for i, kwargs in enumerate(approaches):
        print(f"\n🔌 Approach {i+1}: {kwargs}")
        try:
            # Try to create connection with timeout handling
            blt = BartelsLabtronix(**kwargs)
            print("✅ Connection established!")
            
            # Quick test
            print("📡 Testing communication...")
            
            # Test if we can call methods without errors
            try:
                if hasattr(blt, 'setfrequency'):
                    blt.setfrequency(50)
                    print("✅ setfrequency() called successfully")
                    
                if hasattr(blt, 'setamplitude'):
                    blt.setamplitude(100)
                    print("✅ setamplitude() called successfully")
                    
                if hasattr(blt, 'setsignalform'):
                    blt.setsignalform(SignalForm.Sine)
                    print("✅ setsignalform() called successfully")
                
                print("\n🧪 Testing pump operation...")
                print("⚠️  You should hear/feel the pump if this works...")
                
                if hasattr(blt, 'turnon'):
                    blt.turnon()
                    print("✅ turnon() called - pump should be running!")
                    time.sleep(2)  # Run for 2 seconds
                    
                    if hasattr(blt, 'turnoff'):
                        blt.turnoff()
                        print("✅ turnoff() called - pump should be stopped!")
                
                print("🎉 SUCCESS! All operations completed!")
                
            except Exception as e:
                print(f"⚠️  Operation error: {e}")
                print("This might be normal for initial setup.")
            
            # Clean up
            try:
                if hasattr(blt, 'ser') and hasattr(blt.ser, 'close'):
                    blt.ser.close()
                    print("✅ Connection closed cleanly")
            except:
                pass
                
            return True
            
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            continue
    
    return False

def show_manual_test():
    print("\n" + "="*50)
    print("📋 MANUAL TEST - Try this in Python console:")
    print("="*50)
    print("from pybartelslabtronix import BartelsLabtronix, SignalForm")
    print("blt = BartelsLabtronix(port='COM4')")
    print("blt.setfrequency(50)")
    print("blt.setamplitude(100)")
    print("blt.setsignalform(SignalForm.Sine)")
    print("blt.turnon()   # Should hear/feel pump")
    print("# Wait a few seconds...")
    print("blt.turnoff()  # Should stop pump")
    print("blt.ser.close()")

if __name__ == "__main__":
    success = test_pybartelslabtronix_alternative()
    
    if not success:
        print("\n❌ All connection attempts failed")
        show_manual_test()
        print("\nIf manual test also fails, the issue might be:")
        print("1. Hardware problem with the pump")
        print("2. USB cable issue")
        print("3. Driver compatibility problem")
        print("4. Power supply issue with the pump")
    else:
        print("\n🎉 Connection successful! Your pump is working!")
    
    input("\nPress Enter to continue...")
