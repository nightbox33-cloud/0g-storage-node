// SPDX-License-Identifier: MIT
pragma solidity 0.8.22;

import {IServing} from "../contracts/ledger/LedgerManager.sol";

/// @notice Toy service used by the PoC. It satisfies ERC-165 / IServing so that
/// LedgerManager.registerService accepts it, and its processRefund() LIES about
/// how much ETH was returned. It sends zero ETH.
contract MaliciousService is IServing {
    uint256 public fakeAmount;

    function setFakeAmount(uint256 a) external { fakeAmount = a; }

    function supportsInterface(bytes4 id) external pure returns (bool) {
        // ERC165Checker requires: true for 0x01ffc9a7, false for 0xffffffff,
        // and true for the requested interface id.
        return id == 0x01ffc9a7 || id == type(IServing).interfaceId;
    }

    function accountExists(address, address) external pure override returns (bool) { return true; }
    function getPendingRefund(address, address) external pure override returns (uint) { return 0; }
    function addAccount(address, address, string memory) external payable override {}
    function depositFund(address, address, uint) external payable override {}
    function requestRefundAll(address, address) external override {}
    function deleteAccount(address, address) external override {}

    function processRefund(address, address)
        external view override returns (uint totalAmount, uint balance, uint pendingRefund)
    {
        return (fakeAmount, 0, 0); // no ETH is transferred
    }

    /// @dev Collect the ETH that transferFund() sent here.
    function drain(address to) external {
        payable(to).transfer(address(this).balance);
    }
    receive() external payable {}
}
