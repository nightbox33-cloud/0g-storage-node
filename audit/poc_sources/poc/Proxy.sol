// SPDX-License-Identifier: MIT
pragma solidity 0.8.22;

/// @notice Minimal delegatecall proxy with EMPTY initializer data. This is the
/// state that a BeaconProxy deployed with `data = ""` has before initialize().
contract Proxy {
    address public immutable implementation;
    constructor(address impl_) { implementation = impl_; }

    fallback() external payable {
        address impl = implementation;
        assembly {
            calldatacopy(0, 0, calldatasize())
            let ok := delegatecall(gas(), impl, 0, calldatasize(), 0, 0)
            returndatacopy(0, 0, returndatasize())
            switch ok
            case 0 { revert(0, returndatasize()) }
            default { return(0, returndatasize()) }
        }
    }
    receive() external payable {}
}
