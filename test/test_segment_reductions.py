import torch
from torch.testing._internal.common_device_type import (
    instantiate_device_type_tests,
    dtypes,
    dtypesIfCUDA,
)
from torch.testing._internal.common_utils import (
    TestCase,
    run_tests,
    gradcheck,
)


class TestSegmentReductions(TestCase):
    def _test_simple_1d(self, reduction, device, dtype, unsafe, axis):
        lengths = torch.tensor([1, 2, 3, 0], device=device)
        data = torch.tensor(
            [1, float("nan"), 3, 4, 5, 5],
            device=device,
            dtype=dtype,
            requires_grad=True,
        )
        initial_value = 0
        if reduction == "max":
            expected_result = torch.tensor(
                [1, float("nan"), 5, initial_value], device=device, dtype=dtype
            )
            expected_grad = torch.tensor(
                [1, 1, 0, 0, 0.5, 0.5], device=device, dtype=dtype
            )
        elif reduction == "mean":
            expected_result = torch.tensor(
                [1, float("nan"), 4.666, initial_value], device=device, dtype=dtype
            )
            expected_grad = torch.tensor(
                [1.0, 0.5, 0.5, 0.333, 0.333, 0.333], device=device, dtype=dtype
            )
        actual_result = torch.segment_reduce(
            data=data,
            reduce=reduction,
            lengths=lengths,
            axis=axis,
            unsafe=unsafe,
            initial=initial_value,
        )
        self.assertEqual(
            expected_result, actual_result, rtol=1e-02, atol=1e-05, equal_nan=True
        )

        # TODO: Remove this check once cuda backward support is implemented
        if data.is_cuda:
            return

        # Test backward
        actual_result.sum().backward()
        self.assertEqual(
            expected_grad, data.grad, rtol=1e-02, atol=1e-05, equal_nan=True
        )

        # gradcheck does not work well with bfloat16 or fp16 cpu types
        # also there is small numerical difference with fp32
        if dtype not in [torch.half, torch.bfloat16, torch.float]:
            # gradcheck does not like "nan" input
            data = torch.tensor(
                [1, 10, 3, 4, 5, 5],
                device=device,
                dtype=dtype,
                requires_grad=True,
            )
            self.assertTrue(
                gradcheck(
                    lambda x: torch.segment_reduce(
                        data=x,
                        reduce=reduction,
                        lengths=lengths,
                        axis=axis,
                        unsafe=unsafe,
                        initial=initial_value,
                    ),
                    (data,),
                )
            )

    @dtypesIfCUDA(torch.half, torch.bfloat16, torch.float, torch.double)
    @dtypes(torch.half, torch.bfloat16, torch.float, torch.double)
    def test_simple_1d(self, device, dtype):
        for reduction in ("max", "mean"):
            # TODO: Remove if once mean reduction for cuda is implemented
            if reduction == "mean" and device != "cpu":
                continue
            self._test_simple_1d(reduction, device, dtype, False, 0)
            self._test_simple_1d(reduction, device, dtype, False, -1)
            self._test_simple_1d(reduction, device, dtype, True, 0)
            self._test_simple_1d(reduction, device, dtype, True, -1)


instantiate_device_type_tests(TestSegmentReductions, globals())

if __name__ == "__main__":
    run_tests()
