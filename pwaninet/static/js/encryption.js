/**
 * End-to-End Encryption Utilities
 * Uses Web Crypto API for RSA key generation, encryption, and decryption
 */

class E2EEncryption {
    constructor() {
        this.keyPair = null;
        this.publicKey = null;
        this.privateKey = null;
    }

    /**
     * Generate a new RSA key pair for E2E encryption
     */
    async generateKeyPair() {
        try {
            this.keyPair = await window.crypto.subtle.generateKey(
                {
                    name: "RSA-OAEP",
                    modulusLength: 2048,
                    publicExponent: new Uint8Array([1, 0, 1]),
                    hash: "SHA-256"
                },
                true, // extractable
                ["encrypt", "decrypt"]
            );

            this.publicKey = this.keyPair.publicKey;
            this.privateKey = this.keyPair.privateKey;

            return {
                publicKey: await this.exportPublicKey(),
                privateKey: await this.exportPrivateKey()
            };
        } catch (error) {
            console.error('Error generating key pair:', error);
            throw error;
        }
    }

    /**
     * Export public key to PEM format
     */
    async exportPublicKey() {
        if (!this.publicKey) return null;

        const exported = await window.crypto.subtle.exportKey('spki', this.publicKey);
        const exportedAsString = this.arrayBufferToBase64(exported);
        const pemExported = `-----BEGIN PUBLIC KEY-----\n${exportedAsString.match(/.{1,64}/g).join('\n')}\n-----END PUBLIC KEY-----`;
        return pemExported;
    }

    /**
     * Export private key to PEM format
     */
    async exportPrivateKey() {
        if (!this.privateKey) return null;

        const exported = await window.crypto.subtle.exportKey('pkcs8', this.privateKey);
        const exportedAsString = this.arrayBufferToBase64(exported);
        const pemExported = `-----BEGIN PRIVATE KEY-----\n${exportedAsString.match(/.{1,64}/g).join('\n')}\n-----END PRIVATE KEY-----`;
        return pemExported;
    }

    /**
     * Import public key from PEM format
     */
    async importPublicKey(pemString) {
        // Remove PEM headers and whitespace
        const pemHeader = "-----BEGIN PUBLIC KEY-----";
        const pemFooter = "-----END PUBLIC KEY-----";
        const pemContents = pemString
            .replace(pemHeader, '')
            .replace(pemFooter, '')
            .replace(/\s/g, '');

        const binaryDer = this.base64ToArrayBuffer(pemContents);

        this.publicKey = await window.crypto.subtle.importKey(
            'spki',
            binaryDer,
            {
                name: "RSA-OAEP",
                hash: "SHA-256"
            },
            true,
            ["encrypt"]
        );

        return this.publicKey;
    }

    /**
     * Import private key from PEM format
     */
    async importPrivateKey(pemString) {
        // Remove PEM headers and whitespace
        const pemHeader = "-----BEGIN PRIVATE KEY-----";
        const pemFooter = "-----END PRIVATE KEY-----";
        const pemContents = pemString
            .replace(pemHeader, '')
            .replace(pemFooter, '')
            .replace(/\s/g, '');

        const binaryDer = this.base64ToArrayBuffer(pemContents);

        this.privateKey = await window.crypto.subtle.importKey(
            'pkcs8',
            binaryDer,
            {
                name: "RSA-OAEP",
                hash: "SHA-256"
            },
            true,
            ["decrypt"]
        );

        return this.privateKey;
    }

    /**
     * Encrypt a message using the recipient's public key
     */
    async encryptMessage(message, recipientPublicKeyPem = null) {
        try {
            let publicKey = this.publicKey;

            // If recipient public key is provided, import it
            if (recipientPublicKeyPem) {
                publicKey = await this.importPublicKey(recipientPublicKeyPem);
            }

            if (!publicKey) {
                throw new Error('No public key available for encryption');
            }

            const encoder = new TextEncoder();
            const encodedMessage = encoder.encode(message);

            const encrypted = await window.crypto.subtle.encrypt(
                {
                    name: "RSA-OAEP"
                },
                publicKey,
                encodedMessage
            );

            return this.arrayBufferToBase64(encrypted);
        } catch (error) {
            console.error('Error encrypting message:', error);
            throw error;
        }
    }

    /**
     * Decrypt a message using the private key
     */
    async decryptMessage(encryptedMessageBase64) {
        try {
            if (!this.privateKey) {
                throw new Error('No private key available for decryption');
            }

            const encrypted = this.base64ToArrayBuffer(encryptedMessageBase64);

            const decrypted = await window.crypto.subtle.decrypt(
                {
                    name: "RSA-OAEP"
                },
                this.privateKey,
                encrypted
            );

            const decoder = new TextDecoder();
            return decoder.decode(decrypted);
        } catch (error) {
            console.error('Error decrypting message:', error);
            return '[Encrypted message - decryption failed]';
        }
    }

    /**
     * Generate a random symmetric key for group chats
     */
    async generateSymmetricKey() {
        return await window.crypto.subtle.generateKey(
            {
                name: "AES-GCM",
                length: 256
            },
            true,
            ["encrypt", "decrypt"]
        );
    }

    /**
     * Encrypt with symmetric key (for group chats)
     */
    async encryptSymmetric(message, key) {
        const encoder = new TextEncoder();
        const encoded = encoder.encode(message);

        // Generate IV
        const iv = window.crypto.getRandomValues(new Uint8Array(12));

        const encrypted = await window.crypto.subtle.encrypt(
            {
                name: "AES-GCM",
                iv: iv
            },
            key,
            encoded
        );

        // Combine IV and encrypted data
        const result = new Uint8Array(iv.length + encrypted.byteLength);
        result.set(iv);
        result.set(new Uint8Array(encrypted), iv.length);

        return this.arrayBufferToBase64(result);
    }

    /**
     * Decrypt with symmetric key
     */
    async decryptSymmetric(encryptedBase64, key) {
        try {
            const encrypted = this.base64ToArrayBuffer(encryptedBase64);

            // Extract IV (first 12 bytes)
            const iv = encrypted.slice(0, 12);
            const data = encrypted.slice(12);

            const decrypted = await window.crypto.subtle.decrypt(
                {
                    name: "AES-GCM",
                    iv: iv
                },
                key,
                data
            );

            const decoder = new TextDecoder();
            return decoder.decode(decrypted);
        } catch (error) {
            console.error('Error decrypting symmetric message:', error);
            return '[Encrypted message - decryption failed]';
        }
    }

    /**
     * Convert ArrayBuffer to Base64 string
     */
    arrayBufferToBase64(buffer) {
        const bytes = new Uint8Array(buffer);
        let binary = '';
        for (let i = 0; i < bytes.byteLength; i++) {
            binary += String.fromCharCode(bytes[i]);
        }
        return btoa(binary);
    }

    /**
     * Convert Base64 string to ArrayBuffer
     */
    base64ToArrayBuffer(base64) {
        const binary = atob(base64);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) {
            bytes[i] = binary.charCodeAt(i);
        }
        return bytes.buffer;
    }

    /**
     * Store keys in localStorage (for demo purposes - in production, use secure storage)
     */
    storeKeys(conversationId, publicKey, privateKey) {
        try {
            localStorage.setItem(`e2e_public_key_${conversationId}`, publicKey);
            localStorage.setItem(`e2e_private_key_${conversationId}`, privateKey);
        } catch (error) {
            console.error('Error storing keys:', error);
        }
    }

    /**
     * Load keys from localStorage
     */
    loadKeys(conversationId) {
        try {
            const publicKey = localStorage.getItem(`e2e_public_key_${conversationId}`);
            const privateKey = localStorage.getItem(`e2e_private_key_${conversationId}`);
            return { publicKey, privateKey };
        } catch (error) {
            console.error('Error loading keys:', error);
            return { publicKey: null, privateKey: null };
        }
    }

    /**
     * Initialize encryption for a conversation
     */
    async initForConversation(conversationId) {
        // Try to load existing keys
        const { publicKey, privateKey } = this.loadKeys(conversationId);

        if (publicKey && privateKey) {
            // Import existing keys
            await this.importPublicKey(publicKey);
            await this.importPrivateKey(privateKey);
            return { publicKey, privateKey, isNew: false };
        } else {
            // Generate new keys
            const keys = await this.generateKeyPair();
            this.storeKeys(conversationId, keys.publicKey, keys.privateKey);
            return { ...keys, isNew: true };
        }
    }
}

// Create global instance
window.E2EEncryption = E2EEncryption;
