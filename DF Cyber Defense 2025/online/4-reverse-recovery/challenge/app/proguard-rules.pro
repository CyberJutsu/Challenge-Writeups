# ULTIMATE OBFUSCATION - Obfuscate ALL classes, methods, fields in com.example.pixelblackout
# Repackage all classes into com.example.pixelblackout
-optimizationpasses 7
-dontusemixedcaseclassnames
-dontskipnonpubliclibraryclasses
-verbose

# Custom obfuscation dictionary (ensure obfuscation-dict.txt exists with unique identifiers)
-obfuscationdictionary obfuscation-dict.txt
-classobfuscationdictionary obfuscation-dict.txt
-packageobfuscationdictionary obfuscation-dict.txt

# Flatten package hierarchy into com.example.pixelblackout
-repackageclasses 'com.example.pixelblackout'

# Aggressive obfuscation settings
-allowaccessmodification
-mergeinterfacesaggressively
-overloadaggressively

# Remove all debug information
-renamesourcefileattribute SourceFile

# Obfuscate strings and resources
-adaptclassstrings **
-adaptresourcefilenames **.xml,**.png,**.jpg
-adaptresourcefilecontents **.xml,**.properties

# Minimal Android keeps to ensure app functionality
-keep class * extends android.app.Application {
    public <init>(...);
    public void onCreate();
}
-keep class * extends android.app.Activity {
    public <init>(...);
    public void onCreate(android.os.Bundle);
}
-keepclasseswithmembers class * {
    public <init>(android.content.Context);
    public <init>(android.content.Context, android.util.AttributeSet);
    public <init>(android.content.Context, android.util.AttributeSet, int);
}
-keepclasseswithmembernames class * {
    native <methods>;
}

# Obfuscate ALL classes, methods, and fields in com.example.pixelblackout
-keep,allowobfuscation,allowshrinking class com.example.pixelblackout.** {
    *;
}

# Minimal Data Binding protection
-keep class * implements androidx.databinding.DataBinderMapper {
    public <init>(...);
    public void addMapper(...);
}
-keepclassmembers class com.example.pixelblackout.databinding.** {
    public <init>(...);
    public * get*();
    public * set*();
}

# Room-specific rules (for VaultDatabase)
-keep class * extends androidx.room.RoomDatabase {
    public <init>(...);
}
-keep @androidx.room.Entity class * {
    <fields>;
}
-keep @androidx.room.Dao class * {
    <methods>;
}

# Protect Android resource references
-keepclassmembers class **.R$* {
    public static <fields>;
}

# Aggressive optimizations
-optimizations !code/simplification/arithmetic,!code/simplification/cast,!field/*
-optimizations class/marking/final,class/unboxing/enum,method/marking/final
-optimizations method/removal/parameter,method/marking/static,method/inlining/*
-optimizations code/removal/advanced,code/removal/simple,code/removal/variable
-optimizations code/removal/exception,code/simplification/variable,code/simplification/branch

# Remove all logging
-assumenosideeffects class android.util.Log {
    public static *** d(...);
    public static *** e(...);
    public static *** i(...);
    public static *** v(...);
    public static *** w(...);
    public static *** wtf(...);
}

# Remove reflection and debugging utilities
-assumenosideeffects class java.lang.Class {
    public java.lang.String getName();
    public java.lang.String getSimpleName();
    public java.lang.String getCanonicalName();
}
-assumenosideeffects class java.lang.Object {
    public java.lang.String toString();
}

# Keep essential attributes for libraries
-keepattributes Signature,Annotation,EnclosingMethod,InnerClasses

# Handle warnings for our package only
-dontwarn com.example.pixelblackout.**
