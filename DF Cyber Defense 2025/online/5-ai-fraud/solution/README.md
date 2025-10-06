# FinovaVision

## Writeups from the teams

- [Team ACB](https://www.notion.so/Finovasion-277ac8ececfe800780abeec9f7b3db4d)
- [Team TPBank](https://hieunguyenn.notion.site/CTF-FinovaVision-27704059144f8054bdf2c2b4f1b16360)

## Exploit flow

The system uses **two different FaceNet models**:

- **Login**: `facenet-auth` model (threshold 0.4)
- **Transfer**: `facenet-transaction` model (threshold 0.4)

This creates a **model inconsistency vulnerability** where an adversarial image can:

1. Pass authentication (login succeeds as user `A`)
2. Confuse transaction verification (recognized as user `B` by transaction model)
3. Trigger flag revelation when `from_account != session_user` (user `A` != user `B`)

The adversarial attack is feasible because:

- The similarity threshold is low (0.4)
- We have a leaked user image as the base for creating the adversarial image

**Tip:** If you're not familiar with machine learning concepts, you can ask AI to help you with the creation of the adversarial image ^\_^
