#include <jni.h>
#include <android/log.h>

#include <fstream>
#include <cstdint>
#include <string>
#include <vector>

namespace {
constexpr const char *kTag = "NativeCrypto";

bool g_safe_environment = true;
bool g_secrets_ready = false;
std::vector<uint8_t> g_aes_key;
std::vector<uint8_t> g_aes_iv;
std::vector<uint8_t> g_archive_password;

std::vector<uint8_t> VectorFromArray(JNIEnv *env, jbyteArray array) {
    std::vector<uint8_t> data;
    if (array == nullptr) {
        return data;
    }
    const jsize length = env->GetArrayLength(array);
    if (length <= 0) {
        return data;
    }
    data.resize(length);
    env->GetByteArrayRegion(array, 0, length, reinterpret_cast<jbyte *>(data.data()));
    return data;
}

jbyteArray ArrayFromVector(JNIEnv *env, const std::vector<uint8_t> &data) {
    jbyteArray array = env->NewByteArray(static_cast<jsize>(data.size()));
    if (array == nullptr) {
        return nullptr;
    }
    if (!data.empty()) {
        env->SetByteArrayRegion(array, 0, static_cast<jsize>(data.size()),
                                reinterpret_cast<const jbyte *>(data.data()));
    }
    return array;
}

jbyteArray CloneArray(JNIEnv *env, jbyteArray source) {
    if (source == nullptr) {
        return nullptr;
    }
    std::vector<uint8_t> copy = VectorFromArray(env, source);
    return ArrayFromVector(env, copy);
}

std::string GetStringUtf(JNIEnv *env, jstring value) {
    if (value == nullptr) {
        return {};
    }
    const char *chars = env->GetStringUTFChars(value, nullptr);
    if (chars == nullptr) {
        return {};
    }
    std::string result(chars);
    env->ReleaseStringUTFChars(value, chars);
    return result;
}

jclass FindClass(JNIEnv *env, const std::string &name) {
    jclass clazz = env->FindClass(name.c_str());
    if (clazz == nullptr) {
        __android_log_print(ANDROID_LOG_WARN, kTag, "Failed to find class %s", name.c_str());
    }
    return clazz;
}

jobject CreateSecretKeySpec(JNIEnv *env, const std::vector<uint8_t> &key) {
    jclass secretKeySpecClass = FindClass(env, "javax/crypto/spec/SecretKeySpec");
    if (secretKeySpecClass == nullptr) {
        return nullptr;
    }
    jmethodID ctor = env->GetMethodID(secretKeySpecClass, "<init>", "([BLjava/lang/String;)V");
    if (ctor == nullptr) {
        __android_log_print(ANDROID_LOG_WARN, kTag, "SecretKeySpec.<init> not found");
        env->DeleteLocalRef(secretKeySpecClass);
        return nullptr;
    }
    jbyteArray keyArray = ArrayFromVector(env, key);
    if (keyArray == nullptr) {
        env->DeleteLocalRef(secretKeySpecClass);
        return nullptr;
    }
    jstring algorithm = env->NewStringUTF("AES");
    jobject secretKey = env->NewObject(secretKeySpecClass, ctor, keyArray, algorithm);
    env->DeleteLocalRef(keyArray);
    env->DeleteLocalRef(algorithm);
    env->DeleteLocalRef(secretKeySpecClass);
    return secretKey;
}

jobject CreateIvParameterSpec(JNIEnv *env, const std::vector<uint8_t> &iv) {
    jclass ivClass = FindClass(env, "javax/crypto/spec/IvParameterSpec");
    if (ivClass == nullptr) {
        return nullptr;
    }
    jmethodID ctor = env->GetMethodID(ivClass, "<init>", "([B)V");
    if (ctor == nullptr) {
        __android_log_print(ANDROID_LOG_WARN, kTag, "IvParameterSpec.<init> not found");
        env->DeleteLocalRef(ivClass);
        return nullptr;
    }
    jbyteArray ivArray = ArrayFromVector(env, iv);
    if (ivArray == nullptr) {
        env->DeleteLocalRef(ivClass);
        return nullptr;
    }
    jobject spec = env->NewObject(ivClass, ctor, ivArray);
    env->DeleteLocalRef(ivArray);
    env->DeleteLocalRef(ivClass);
    return spec;
}

jobject AcquireCipher(JNIEnv *env, jint mode, const std::vector<uint8_t> &key,
                      const std::vector<uint8_t> &iv) {
    jclass cipherClass = FindClass(env, "javax/crypto/Cipher");
    if (cipherClass == nullptr) {
        return nullptr;
    }
    jmethodID getInstance = env->GetStaticMethodID(cipherClass, "getInstance",
                                                   "(Ljava/lang/String;)Ljavax/crypto/Cipher;");
    if (getInstance == nullptr) {
        __android_log_print(ANDROID_LOG_WARN, kTag, "Cipher.getInstance not found");
        env->DeleteLocalRef(cipherClass);
        return nullptr;
    }
    jstring transformation = env->NewStringUTF("AES/CBC/PKCS5Padding");
    jobject cipher = env->CallStaticObjectMethod(cipherClass, getInstance, transformation);
    env->DeleteLocalRef(transformation);
    if (cipher == nullptr || env->ExceptionCheck()) {
        env->ExceptionClear();
        env->DeleteLocalRef(cipherClass);
        __android_log_print(ANDROID_LOG_WARN, kTag, "Failed to instantiate Cipher");
        return nullptr;
    }

    jobject secretKey = CreateSecretKeySpec(env, key);
    jobject ivSpec = CreateIvParameterSpec(env, iv);
    if (secretKey == nullptr || ivSpec == nullptr) {
        if (secretKey != nullptr) env->DeleteLocalRef(secretKey);
        if (ivSpec != nullptr) env->DeleteLocalRef(ivSpec);
        env->DeleteLocalRef(cipher);
        env->DeleteLocalRef(cipherClass);
        return nullptr;
    }

    jmethodID init = env->GetMethodID(cipherClass, "init",
                                      "(ILjava/security/Key;Ljava/security/spec/AlgorithmParameterSpec;)V");
    if (init == nullptr) {
        __android_log_print(ANDROID_LOG_WARN, kTag, "Cipher.init not found");
        env->DeleteLocalRef(secretKey);
        env->DeleteLocalRef(ivSpec);
        env->DeleteLocalRef(cipher);
        env->DeleteLocalRef(cipherClass);
        return nullptr;
    }

    env->CallVoidMethod(cipher, init, mode, secretKey, ivSpec);
    env->DeleteLocalRef(secretKey);
    env->DeleteLocalRef(ivSpec);
    env->DeleteLocalRef(cipherClass);
    if (env->ExceptionCheck()) {
        env->ExceptionClear();
        env->DeleteLocalRef(cipher);
        __android_log_print(ANDROID_LOG_WARN, kTag, "Cipher.init threw");
        return nullptr;
    }

    return cipher;
}

jbyteArray CipherDoFinal(JNIEnv *env, jobject cipher, jbyteArray input) {
    if (cipher == nullptr || input == nullptr) {
        return nullptr;
    }
    jclass cipherClass = env->GetObjectClass(cipher);
    jmethodID doFinal = env->GetMethodID(cipherClass, "doFinal", "([B)[B");
    jbyteArray result = (jbyteArray) env->CallObjectMethod(cipher, doFinal, input);
    env->DeleteLocalRef(cipherClass);
    if (env->ExceptionCheck()) {
        env->ExceptionClear();
        return nullptr;
    }
    return result;
}

jbyteArray Base64Decode(JNIEnv *env, jstring data) {
    jclass base64Class = FindClass(env, "android/util/Base64");
    if (base64Class == nullptr) {
        return nullptr;
    }
    jmethodID decode = env->GetStaticMethodID(base64Class, "decode",
                                              "(Ljava/lang/String;I)[B");
    if (decode == nullptr) {
        env->DeleteLocalRef(base64Class);
        __android_log_print(ANDROID_LOG_WARN, kTag, "Base64.decode not found");
        return nullptr;
    }
    const jint flags = 0; // DEFAULT
    jbyteArray result = (jbyteArray) env->CallStaticObjectMethod(base64Class, decode, data, flags);
    env->DeleteLocalRef(base64Class);
    if (env->ExceptionCheck()) {
        env->ExceptionClear();
        return nullptr;
    }
    return result;
}

jstring Base64Encode(JNIEnv *env, jbyteArray data) {
    jclass base64Class = FindClass(env, "android/util/Base64");
    if (base64Class == nullptr) {
        return nullptr;
    }
    jmethodID encode = env->GetStaticMethodID(base64Class, "encodeToString",
                                              "([BI)Ljava/lang/String;");
    if (encode == nullptr) {
        env->DeleteLocalRef(base64Class);
        __android_log_print(ANDROID_LOG_WARN, kTag, "Base64.encodeToString not found");
        return nullptr;
    }
    const jint flags = 2; // NO_WRAP
    jstring result = (jstring) env->CallStaticObjectMethod(base64Class, encode, data, flags);
    env->DeleteLocalRef(base64Class);
    if (env->ExceptionCheck()) {
        env->ExceptionClear();
        return nullptr;
    }
    return result;
}

jbyteArray MessageDigestDigest(JNIEnv *env, const char *algorithm, jbyteArray data) {
    jclass digestClass = FindClass(env, "java/security/MessageDigest");
    if (digestClass == nullptr) {
        return nullptr;
    }
    jmethodID getInstance = env->GetStaticMethodID(digestClass, "getInstance",
                                                   "(Ljava/lang/String;)Ljava/security/MessageDigest;");
    if (getInstance == nullptr) {
        env->DeleteLocalRef(digestClass);
        __android_log_print(ANDROID_LOG_WARN, kTag, "MessageDigest.getInstance not found");
        return nullptr;
    }
    jstring algoStr = env->NewStringUTF(algorithm);
    jobject digest = env->CallStaticObjectMethod(digestClass, getInstance, algoStr);
    env->DeleteLocalRef(algoStr);
    if (digest == nullptr || env->ExceptionCheck()) {
        env->ExceptionClear();
        env->DeleteLocalRef(digestClass);
        __android_log_print(ANDROID_LOG_WARN, kTag, "Failed to obtain MessageDigest");
        return nullptr;
    }
    jmethodID digestMethod = env->GetMethodID(digestClass, "digest", "([B)[B");
    if (digestMethod == nullptr) {
        env->DeleteLocalRef(digest);
        env->DeleteLocalRef(digestClass);
        __android_log_print(ANDROID_LOG_WARN, kTag, "MessageDigest.digest not found");
        return nullptr;
    }
    jbyteArray digestBytes = (jbyteArray) env->CallObjectMethod(digest, digestMethod, data);
    env->DeleteLocalRef(digest);
    env->DeleteLocalRef(digestClass);
    if (env->ExceptionCheck()) {
        env->ExceptionClear();
        return nullptr;
    }
    return digestBytes;
}

bool ContainsInFile(const std::string &path, const std::string &needle) {
    std::ifstream stream(path);
    if (!stream.is_open()) {
        return false;
    }
    std::string line;
    while (std::getline(stream, line)) {
        if (line.find(needle) != std::string::npos) {
            return true;
        }
    }
    return false;
}

bool CheckEnvironment() {
    const bool fridaPresent = ContainsInFile("/proc/net/unix", "frida");
    if (fridaPresent) {
        __android_log_print(ANDROID_LOG_WARN, kTag, "Frida socket detected");
        return false;
    }
    return true;
}

bool EnsureSecretsReady() {
    if (!g_secrets_ready || g_aes_key.empty() || g_aes_iv.empty() || g_archive_password.empty()) {
        __android_log_print(ANDROID_LOG_WARN, kTag, "Secret material unavailable");
        return false;
    }
    return true;
}

void SetSecrets(const std::vector<uint8_t> &key,
                const std::vector<uint8_t> &iv,
                const std::vector<uint8_t> &password) {
    g_aes_key = key;
    g_aes_iv = iv;
    g_archive_password = password;
    g_secrets_ready = !g_aes_key.empty() && !g_aes_iv.empty() && !g_archive_password.empty();
}

jstring NativeEncryptString(JNIEnv *env, jclass, jstring plaintext) {
    if (!EnsureSecretsReady()) {
        return env->NewStringUTF("");
    }
    std::string utf = GetStringUtf(env, plaintext);
    std::vector<uint8_t> bytes(utf.begin(), utf.end());
    jbyteArray plainBytes = ArrayFromVector(env, bytes);
    if (plainBytes == nullptr) {
        return env->NewStringUTF("");
    }
    jobject cipher = AcquireCipher(env, 1, g_aes_key, g_aes_iv);
    if (cipher == nullptr) {
        env->DeleteLocalRef(plainBytes);
        return env->NewStringUTF("");
    }
    jbyteArray encrypted = CipherDoFinal(env, cipher, plainBytes);
    env->DeleteLocalRef(cipher);
    env->DeleteLocalRef(plainBytes);
    if (encrypted == nullptr) {
        return env->NewStringUTF("");
    }
    jstring encoded = Base64Encode(env, encrypted);
    env->DeleteLocalRef(encrypted);
    if (encoded == nullptr) {
        return env->NewStringUTF("");
    }
    return encoded;
}

jstring NativeDecryptString(JNIEnv *env, jclass, jstring payload) {
    if (!EnsureSecretsReady()) {
        return env->NewStringUTF("");
    }
    jbyteArray decoded = Base64Decode(env, payload);
    if (decoded == nullptr) {
        return env->NewStringUTF("");
    }
    jobject cipher = AcquireCipher(env, 2, g_aes_key, g_aes_iv);
    if (cipher == nullptr) {
        env->DeleteLocalRef(decoded);
        return env->NewStringUTF("");
    }
    jbyteArray plainBytes = CipherDoFinal(env, cipher, decoded);
    env->DeleteLocalRef(cipher);
    env->DeleteLocalRef(decoded);
    if (plainBytes == nullptr) {
        return env->NewStringUTF("");
    }
    std::vector<uint8_t> data = VectorFromArray(env, plainBytes);
    env->DeleteLocalRef(plainBytes);
    return env->NewStringUTF(std::string(data.begin(), data.end()).c_str());
}

jbyteArray NativeEncryptArchive(JNIEnv *env, jclass, jbyteArray payload) {
    if (!EnsureSecretsReady()) {
        return CloneArray(env, payload);
    }
    jbyteArray passwordBytes = ArrayFromVector(env, g_archive_password);
    if (passwordBytes == nullptr) {
        return CloneArray(env, payload);
    }
    jbyteArray keyDigest = MessageDigestDigest(env, "MD5", passwordBytes);
    jbyteArray ivDigest = MessageDigestDigest(env, "SHA-256", passwordBytes);
    env->DeleteLocalRef(passwordBytes);
    if (keyDigest == nullptr || ivDigest == nullptr) {
        if (keyDigest != nullptr) env->DeleteLocalRef(keyDigest);
        if (ivDigest != nullptr) env->DeleteLocalRef(ivDigest);
        return CloneArray(env, payload);
    }
    std::vector<uint8_t> key = VectorFromArray(env, keyDigest);
    std::vector<uint8_t> iv = VectorFromArray(env, ivDigest);
    env->DeleteLocalRef(keyDigest);
    env->DeleteLocalRef(ivDigest);
    if (iv.size() >= 16) {
        iv.resize(16);
    }
    jobject cipher = AcquireCipher(env, 1, key, iv);
    if (cipher == nullptr) {
        return CloneArray(env, payload);
    }
    jbyteArray encrypted = CipherDoFinal(env, cipher, payload);
    env->DeleteLocalRef(cipher);
    return encrypted;
}

void NativeConfigureSecrets(JNIEnv *env, jclass, jint mask, jbyteArray keyArray,
                            jbyteArray ivArray, jbyteArray passwordArray) {
    const uint8_t xorMask = static_cast<uint8_t>(mask & 0xFF);
    std::vector<uint8_t> key = VectorFromArray(env, keyArray);
    std::vector<uint8_t> iv = VectorFromArray(env, ivArray);
    std::vector<uint8_t> password = VectorFromArray(env, passwordArray);

    for (auto &byte : key) {
        byte ^= xorMask;
    }
    for (auto &byte : iv) {
        byte ^= xorMask;
    }
    for (auto &byte : password) {
        byte ^= xorMask;
    }

    SetSecrets(key, iv, password);
}

jboolean NativeOkToRun(JNIEnv *, jclass) {
    return g_safe_environment ? JNI_TRUE : JNI_FALSE;
}

} // namespace

JNIEXPORT jint JNICALL JNI_OnLoad(JavaVM *vm, void *) {
    JNIEnv *env = nullptr;
    if (vm->GetEnv(reinterpret_cast<void **>(&env), JNI_VERSION_1_6) != JNI_OK) {
        return JNI_ERR;
    }

    g_safe_environment = CheckEnvironment();

    const char *class_name = "com/example/pixelblackout/nativebridge/NativeCrypto";
    jclass clazz = env->FindClass(class_name);
    if (clazz == nullptr) {
        __android_log_print(ANDROID_LOG_ERROR, kTag, "Failed to locate %s", class_name);
        return JNI_ERR;
    }

    static const JNINativeMethod kMethods[] = {
            {"nativeEncryptString", "(Ljava/lang/String;)Ljava/lang/String;", (void *) NativeEncryptString},
            {"nativeDecryptString", "(Ljava/lang/String;)Ljava/lang/String;", (void *) NativeDecryptString},
            {"nativeEncryptArchive", "([B)[B", (void *) NativeEncryptArchive},
            {"nativeConfigure", "(I[B[B[B)V", (void *) NativeConfigureSecrets},
            {"nativeOkToRun", "()Z", (void *) NativeOkToRun},
    };

    if (env->RegisterNatives(clazz, kMethods, sizeof(kMethods) / sizeof(kMethods[0])) != JNI_OK) {
        __android_log_print(ANDROID_LOG_ERROR, kTag, "RegisterNatives failed");
        env->DeleteLocalRef(clazz);
        return JNI_ERR;
    }

    env->DeleteLocalRef(clazz);
    return JNI_VERSION_1_6;
}
