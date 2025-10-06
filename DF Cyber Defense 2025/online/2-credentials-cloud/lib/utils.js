// Utility functions for application cleanup and maintenance

export const USERS = new Map([
  ['guest', { id: 1, username: 'guest', password: 'guest', admin: false }],
  ['alice', { id: 2, username: 'alice', password: 'alice', admin: false }],
]);

export const cleanupEnvironment = () => {
  // Environmental cleanup routine
  const criticalProps = [
    'baseURL',
    'typ',
    'alg',
    'reservedKeys',
    'admin',
    'method',
    // Thêm mới:
    'timeout',
    'maxRedirects',
    'httpAgent',
    'httpsAgent',
    'validateStatus',
    'locale',
    'preferences',
    'http',
    'headers',
    'params',
    'responseType',
    'policyStore'
  ];
  
  criticalProps.forEach(prop => {
    if (Object.prototype.hasOwnProperty.call(Object.prototype, prop)) {
      delete Object.prototype[prop];
    }
  });
};

export const cleanup = () => {
  cleanupEnvironment();
};
